# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, date, timedelta
import json
import os
import uuid

from decimal import *
from delorean import epoch
from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric, Index
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from gryphon.lib.money import Money
from gryphon.lib import gryphon_json_serialize
from gryphon.lib.exchange.exchange_factory import make_exchange_from_key
from gryphon.lib.models.base import Base
from gryphon.lib.models.basic_order import BasicOrder
from gryphon.lib.models.datum import Datum
from gryphon.lib.models.trade import Trade

metadata = Base.metadata


class Order(Base, BasicOrder):
    __tablename__ = 'order'
    
    order_id = Column(Integer, primary_key=True)
    status = Column(Unicode(32), nullable=False)
    order_type = Column(Unicode(64))
    unique_id = Column(Unicode(64), nullable=False)
    exchange_order_id = Column(Unicode(64))
    actor = Column(Unicode(64))
    exchange_rate = Column(Numeric(precision=20, scale=10))
    
    time_created = Column(DateTime, nullable=False)
    time_executed = Column(DateTime)

    _exchange_name = Column('exchange_name', Unicode(64))
    _price = Column('price', Numeric(precision=20, scale=10))
    _price_currency = Column('price_currency', Unicode(64))
    _volume = Column('volume', Numeric(precision=20, scale=10))
    _volume_currency = Column('volume_currency', Unicode(64))
    _fundamental_value = Column('fundamental_value', Numeric(precision=20, scale=10))
    _fundamental_value_currency = Column('fundamental_value_currency', Unicode(3))
    _competitiveness = Column('competitiveness', Numeric(precision=20, scale=10))
    _competitiveness_currency = Column('competitiveness_currency', Unicode(3))
    _spread = Column('spread', Numeric(precision=20, scale=10))
    _spread_currency = Column('spread_currency', Unicode(3))
    
    trades = relationship('Trade', cascade="all,delete-orphan", backref='order')
    datums = relationship("Datum",  backref='order')
    
    __table_args__ = (Index('idx_exchange_order_id_exchange_name', exchange_order_id, _exchange_name),
                      Index('idx_status', status),)
    
    def __init__(self, actor, mode, volume, price, exchange, exchange_order_id):
        self.status = self.OPEN
        self.unique_id = unicode(uuid.uuid4().hex)
        self.time_created = datetime.utcnow()

        assert actor and price and volume and exchange and mode
        self.actor = actor
        self.order_type = mode.upper()
        self.price = price
        self.volume = volume
        self.exchange = exchange
        self.exchange_order_id = exchange_order_id
        self.currency = self.exchange.currency

    def __unicode__(self):
        return u'[ORDER:%s:%s] Status:%s, Price:%s, Volume:%s BTC' % (
            self.order_type, self.exchange.name, self.status, self.price, self.volume)
        
    def __repr__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps({
            'order_id':self.order_id,
            'unique_id':self.unique_id,
            'exchange_order_id':self.exchange_order_id,
            'time_created':unicode(self.time_created),
            'time_executed':unicode(self.time_executed),
            'exchange':self.exchange.name,
            'status':self.status,
            'order_type': self.order_type,
            'price':self.price,
            'volume':self.volume,
            'trades': ["%s @ %s" % (t.volume, t.price) for t in self.trades]
        }, ensure_ascii=False)

    def set_trades(self, trades):
        self.trades = []
        for trade in trades:
            new_trade = Trade(
                self.order_type,
                trade['fiat'],
                trade['fee'],
                trade[self._volume_currency.lower()],
                trade['trade_id'],
                self)

            new_trade.time_created = epoch(trade['time']).datetime

    # returns position change
    def was_eaten(self, order_details):
        old_position = self.calc_position()
        old_position_no_fees = self.calc_position(include_fees=False)

        self.time_executed = datetime.utcnow()

        if order_details['%s_total' % self._volume_currency.lower()] <= 0:
            self.status = Order.CANCELLED
        else:
            self.status = Order.FILLED
            # TODO store the volume filled amount in order?
            self.time_executed = datetime.utcnow()
            self.set_trades(order_details['trades'])

        position_change = self.position_change(old_position)
        position_change_no_fees = self.position_change(
            old_position_no_fees,
            include_fees=False,
        )

        return position_change, position_change_no_fees

    # returns position change
    def was_partially_eaten(self, order_details):
        old_position = self.calc_position()
        old_position_no_fees = self.calc_position(include_fees=False)

        self.set_trades(order_details['trades'])

        position_change = self.position_change(old_position)
        position_change_no_fees = self.position_change(old_position_no_fees, include_fees=False)

        return position_change, position_change_no_fees

    # returns position change
    def reverse(self):
        old_position = self.position
        self.status = Order.REVERSED
        self.set_trades([])
        return self.position_change(old_position)

    @property
    def exchange(self):
        if hasattr(self, '_exchange'):
            return self._exchange
        elif self._exchange_name:
            self._exchange = make_exchange_from_key(self._exchange_name)
            return self._exchange
        else:
            return None
        
    @exchange.setter
    def exchange(self, value):
        self._exchange = value
        self._exchange_name = self._exchange.name
    
    
    @property
    def volume(self):
        if not self._volume:
            return None
        return Money(self._volume, self._volume_currency)

    @volume.setter
    def volume(self, value):
        self._volume = value.amount
        self._volume_currency = value.currency
    
    @property
    def price(self):
        if not self._price:
            return None
        return Money(self._price, self._price_currency)

    @price.setter
    def price(self, value):
        self._price = value.amount
        self._price_currency = value.currency

    @property
    def competitiveness(self):
        return Money(self._competitiveness, self._competitiveness_currency)

    @competitiveness.setter
    def competitiveness(self, value):
        self._competitiveness = value.amount
        self._competitiveness_currency = value.currency

    @property
    def fundamental_value(self):
        if not self._fundamental_value:
            return None
        return Money(self._fundamental_value, self._fundamental_value_currency)

    @fundamental_value.setter
    def fundamental_value(self, value):
        self._fundamental_value = value.amount
        self._fundamental_value_currency = value.currency

    @property
    def spread(self):
        if not self._spread:
            return None
        return Money(self._spread, self._spread_currency)

    @spread.setter
    def spread(self, value):
        self._spread = value.amount
        self._spread_currency = value.currency
    
    @property
    def volume_filled(self):
        return sum([t.volume for t in self.trades], Money("0", self._volume_currency))

    @property
    def volume_remaining(self):
        return self.volume - self.volume_filled

    # Included for backwards compatibility. New code should call calc_position()
    @property
    def position(self):
        return self.calc_position()

    def calc_position(self, include_fees=True):
        from gryphon.lib.models.exchange import Position
        return sum([t.calc_position(include_fees=include_fees) for t in self.trades], Position())
