# -*- coding: utf-8 -*-
from gryphon.lib.models.emeraldhavoc.base import EmeraldHavocBase
import json
import uuid
from decimal import *

from gryphon.lib.money import Money
from datetime import datetime
from sqlalchemy import Column, Integer, Unicode, DateTime, Numeric
from sqlalchemy.ext.declarative import declarative_base

metadata = EmeraldHavocBase.metadata


class ExchangeVolume(EmeraldHavocBase):
    __tablename__ = 'exchange_volume'

    exchange_volume_id = Column(Integer, primary_key=True)
    unique_id = Column(Unicode(64), nullable=False)
    exchange = Column(Unicode(64), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    time_created = Column(DateTime, nullable=False)
    _exchange_volume = Column('exchange_volume', Numeric(precision=20, scale=10))

    def __init__(self, exchange_volume, exchange, timestamp):
        self.unique_id = unicode(uuid.uuid4().hex)
        self.time_created = datetime.utcnow()
        self.timestamp = timestamp
        self.exchange_volume = exchange_volume
        self.exchange = exchange

    def __unicode__(self):
        return u'[EXCHANGE VOLUME - Exchange:%s] Volume:%s,' % (
            self.exchange, self.exchange_volume)

    def __repr__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps({
            'exchange_volume_id': self.exchange_volume_id,
            'time_created': unicode(self.time_created),
            'unique_id': self.unique_id,
            'exchange': self.exchange,
            'exchange_volume': self.exchange_volume
        }, ensure_ascii=False)

    @property
    def exchange_volume(self):
        return Money(self._exchange_volume, 'BTC')

    @exchange_volume.setter
    def exchange_volume(self, value):
        if isinstance(value, Money) and value.currency == 'BTC':
            self._exchange_volume = value.amount
        else:
            raise ValueError('exchange_volume must be a BTC Money object')
