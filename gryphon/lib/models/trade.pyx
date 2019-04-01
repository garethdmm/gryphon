# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, date, timedelta
import json
import os
import uuid

from decimal import *
from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func
from sqlalchemy.sql import expression
from sqlalchemy import and_

from gryphon.lib import gryphon_json_serialize
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_factory import make_exchange_from_key
from gryphon.lib.models.base import Base
from gryphon.lib.money import Money

metadata = Base.metadata


class Trade(Base):
    __tablename__ = 'trade'
    
    #Trade Types
    BID = Consts.BID
    ASK = Consts.ASK
    
    trade_id = Column(Integer, primary_key=True)
    trade_type = Column(Unicode(64))
    unique_id = Column(Unicode(64), nullable=False)
    exchange_trade_id = Column(Unicode(64))
    time_created = Column(DateTime, nullable=False)
    
    _fee = Column('fee', Numeric(precision=24, scale=14))
    _fee_currency = Column('fee_currency', Unicode(3))
    _price = Column('price', Numeric(precision=24, scale=14))
    _price_currency = Column('price_currency', Unicode(3))
    _volume = Column('volume', Numeric(precision=24, scale=14))
    _volume_currency = Column('volume_currency', Unicode(3))

    meta_data = Column('meta_data', UnicodeText(length=2**31))

    # Some Trades have BTC fees, which reduce our total BTC assets. Every once in a while
    # we create a "buyback" transaction where we buy back those fees outside our trading system.
    # We then mark the fee as "bought back" by setting the trade's fee_buyback_transaction
    fee_buyback_transaction_id = Column(Integer, ForeignKey('transaction.transaction_id'))
    fee_buyback_transaction = relationship("Transaction",  backref='fee_buyback_trades')

    order_id = Column(Integer, ForeignKey('order.order_id'))
    
    def __init__(self, trade_type, price, fee,  volume, exchange_trade_id, order, meta_data={}):
        self.unique_id = unicode(uuid.uuid4().hex)
        self.time_created = datetime.utcnow()
        self.trade_type = trade_type
        self.price = price
        self.fee = fee
        self.volume = volume
        self.exchange_trade_id = exchange_trade_id
        self.order = order
        self.meta_data = json.dumps(meta_data)
        
    def __unicode__(self):
        return u'[TRADE:%s, Order:%s] Price:%s, Volume:%s BTC, Exchange:%s' % (
            self.trade_type, self.order_id, self.price, self.volume, self.order.exchange.name)
        
    def __repr__(self):
        return self.to_json()
    
    def to_json(self):
        return json.dumps({
            'trade_id':self.trade_id,
            'trade_type':self.trade_type,
            'time_created':unicode(self.time_created),
            'unique_id':self.unique_id,
            'exchange_trade_id':self.exchange_trade_id,
            'order_id':self.order_id,
            'fee':self.fee,
            'price':self.price,
            'volume':self.volume
        }, ensure_ascii=False)
    
    @property
    def volume(self):
        return Money(self._volume, self._volume_currency)

    @volume.setter
    def volume(self, value):
        self._volume = value.amount
        self._volume_currency = value.currency

    @property
    def price(self):
        return Money(self._price, self._price_currency)

    @price.setter
    def price(self, value):
        self._price = value.amount
        self._price_currency = value.currency

    @hybrid_property
    def price_in_usd(self):
        """
        Regular property you can call on a loaded trade in python. Returns a USD Money object
        """
        exchange_rate_to_usd = self.exchange_rate
        return Money(self._price * exchange_rate_to_usd, 'USD')

    @price_in_usd.expression
    def price_in_usd(cls):
        """
        SQL Expression which lets us calculate and use USD prices in SQL.

        Must have Order joined in queries where it is used.
        Ex: db.query(func.sum(Trade.price_in_usd)).join(Order).scalar()
        This gives decimal results, since we don't have our Money objects in SQL
        """
        from gryphon.lib.models.order import Order

        exchange_rate_to_usd = Order.exchange_rate
        return cls._price * exchange_rate_to_usd

    @property
    def fee(self):
        return Money(self._fee, self._fee_currency)

    @fee.setter
    def fee(self, value):
        self._fee = value.amount
        self._fee_currency = value.currency

    @hybrid_property
    def fee_in_usd(self):
        """
        Regular property you can call on a loaded trade in python. Returns a USD Money object
        """
        if self._fee_currency == 'BTC':
            exchange_rate_to_usd = self.fundamental_value.amount * self.exchange_rate
        else:
            exchange_rate_to_usd = self.exchange_rate

        return Money(self._fee * exchange_rate_to_usd, 'USD')

    @fee_in_usd.expression
    def fee_in_usd(cls):
        """
        SQL Expression which lets us calculate and use USD fees in SQL (usually for summing).

        Must have Order joined in queries where it is used.
        Ex: db.query(func.sum(Trade.fee_in_usd)).join(Order).scalar()
        This gives decimal results, since we don't have our Money objects in SQL
        """
        from gryphon.lib.models.order import Order

        exchange_rate_to_usd = expression.case(
            [(cls._fee_currency == 'BTC', Order._fundamental_value * Order.exchange_rate)],
            else_=Order.exchange_rate,
        )

        return cls._fee * exchange_rate_to_usd

    @hybrid_property
    def has_outstanding_btc_fee(self):
        return self._fee_currency == 'BTC' and self.fee_buyback_transaction_id == None

    @has_outstanding_btc_fee.expression
    def has_outstanding_btc_fee(cls):
        return and_(cls._fee_currency == 'BTC', cls.fee_buyback_transaction_id == None)

    # Included for backwards compatibility. New code should call calc_position()
    @property
    def position(self):
        return self.calc_position()

    def calc_position(self, include_fees=True):
        from gryphon.lib.models.exchange import Position
        position = Position()

        if self.trade_type == self.BID:
            position -= self.price
            position += self.volume
        else: #ASK
            position += self.price
            position -= self.volume

        if include_fees:
            position -= self.fee

        return position

    # kinda janky, this is used when we are copying trade objects and need to keep their
    # exchange_rate around without references to their parent order.
    # used in gryphon.lib.gryphonfury.profit:copy_trade()
    @property
    def exchange_rate(self):
        if self.order:
            return self.order.exchange_rate
        elif self._exchange_rate:
            return self._exchange_rate
        return None

    @property
    def fundamental_value(self):
        if self.order:
            return self.order.fundamental_value
        elif self._fundamental_value:
            return self._fundamental_value
        return None

    @property
    def exchange_name(self):
        if self.order:
            return self.order._exchange_name
        elif self._exchange_name:
            return self._exchange_name
        return None

    def convert_to_currency(self, amount, currency):
        if amount.currency == currency:
            return amount
        elif currency == "USD":
            return amount.to("USD", exchange_rate_to_usd=self.exchange_rate)
        else:
            raise ValueError(
                "Cannot to convert trade price into %s (Only USD supported)" % currency,
            )

    def price_in_currency(self, currency):
        return self.convert_to_currency(self.price, currency)

    def fee_in_currency(self, currency):
        if self.fee.currency == "BTC":
            fundamental_value = self.fundamental_value
            # converts BTC fee into currency of fundamental_value
            fee = fundamental_value * self.fee.amount
        else:
            fee = self.fee
        return self.convert_to_currency(fee, currency)
