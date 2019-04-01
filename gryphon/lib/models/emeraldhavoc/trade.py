# -*- coding: utf-8 -*-
import os
from gryphon.lib.models.emeraldhavoc.base import EmeraldHavocBase
import json
import uuid
from decimal import *
from collections import defaultdict

from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_factory import make_exchange_from_key
from gryphon.lib import gryphon_json_serialize
from datetime import datetime, date, timedelta
from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

metadata = EmeraldHavocBase.metadata


class Trade(EmeraldHavocBase):
    __tablename__ = 'trade'

    trade_id = Column(Integer, primary_key=True)
    unique_id = Column(Unicode(64), nullable=False)
    exchange = Column(Unicode(64), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    time_created = Column(DateTime, nullable=False)
    exchange_trade_id = Column(Unicode(64), nullable=True)
    source = Column(Unicode(64), nullable=False)

    _price = Column('price', Numeric(precision=20, scale=10))
    _price_currency = Column('price_currency', Unicode(3))
    _volume = Column('volume', Numeric(precision=20, scale=10))
    _volume_currency = Column('volume_currency', Unicode(3))

    __table_args__ = (
        UniqueConstraint(exchange, exchange_trade_id, name='uniq_exchange_exchange_trade_id'),
    )

    def __init__(self, price, volume, exchange, timestamp, exchange_trade_id, source='EXCHANGE'):
        self.unique_id = unicode(uuid.uuid4().hex)
        self.time_created = datetime.utcnow()
        self.timestamp = timestamp
        self.price = price
        self.volume = volume
        self.exchange = exchange
        self.exchange_trade_id = exchange_trade_id
        self.source = source

    def __unicode__(self):
        return u'[TRADE - Exchange:%s] Price:%s, Volume:%s BTC, Exchange:%s' % (
            self.exchange, self.price, self.volume, self.exchange)

    def __repr__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps({
            'trade_id':self.trade_id,
            'timestamp':unicode(self.timestamp),
            'unique_id':self.unique_id,
            'exchange':self.exchange,
            'price':self.price,
            'volume':self.volume
        }, ensure_ascii=False)

    @property
    def volume(self):
        return Money(self._volume, self._volume_currency)

    @volume.setter
    def volume(self, value):
        self._volume = value.amount
        self._volume_currency = unicode(value.currency)

    @property
    def price(self):
        return Money(self._price, self._price_currency)

    @price.setter
    def price(self, value):
        self._price = value.amount
        self._price_currency = unicode(value.currency)
