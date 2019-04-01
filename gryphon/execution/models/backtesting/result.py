# -*- coding: utf-8 -*-
from datetime import datetime
import uuid

from sqlalchemy import Column, Unicode, UnicodeText, DateTime, Integer, Numeric
from sqlalchemy.orm import relationship, backref

from gryphon.lib.models.base import Base
from gryphon.lib.money import Money

metadata = Base.metadata


class Result(Base):
    __tablename__ = 'result'

    result_id = Column(Integer, primary_key=True)
    ticks = Column(Integer, nullable=False)
    unique_id = Column(Unicode(64), nullable=False)
    algorithm = Column(Unicode(64), nullable=False)
    batch = Column(Unicode(64), nullable=False)
    _trading_volume = Column('trading_volume', Numeric(precision=20, scale=10))
    _usd = Column('usd', Numeric(precision=20, scale=10))
    _btc = Column('btc', Numeric(precision=20, scale=10))
    time_created = Column(DateTime, nullable=False)
    
    trades = relationship('ResultTrade', cascade="all,delete-orphan", backref='result')
    
    def __init__(self, usd, btc, trading_volume, algorithm, batch, ticks):
        self.unique_id = unicode(uuid.uuid4().hex)
        self.time_created = datetime.utcnow()
        self.algorithm = algorithm
        self.batch = batch
        self.usd = usd
        self.btc = btc
        self.ticks = ticks
        self.trading_volume = trading_volume
    
    @property
    def trading_volume(self):
        return Money(self._trading_volume, 'BTC')

    @trading_volume.setter
    def trading_volume(self, value):
        self._trading_volume = value.amount
    
    @property
    def btc(self):
        return Money(self._btc, 'BTC')

    @btc.setter
    def btc(self, value):
        self._btc = value.amount

    @property
    def usd(self):
        return Money(self._usd, 'USD')

    @usd.setter
    def usd(self, value):
        self._usd = value.amount
    
