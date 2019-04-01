# -*- coding: utf-8 -*-
from cdecimal import *
from datetime import datetime, date, timedelta
import json
import os
import uuid

from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

from gryphon.execution.models.backtesting.result import Result
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.models.base import Base
from gryphon.lib.money import Money

metadata = Base.metadata


class ResultTrade(Base):
    __tablename__ = 'result_trade'
    
    trade_id = Column(Integer, primary_key=True)
    
    _price = Column('price', Numeric(precision=20, scale=10))
    _price_currency = Column('price_currency', Unicode(3))
    _volume = Column('volume', Numeric(precision=20, scale=10))
    _volume_currency = Column('volume_currency', Unicode(3))
    tick = Column(Integer)
    
    user_trade = Column(Unicode(64))
    result_id = Column(Integer, ForeignKey('result.result_id'))
    
    def __init__(self, trade_obj):
        self.price = trade_obj.price
        self.volume = trade_obj.volume
        self.tick = trade_obj.tick
        if trade_obj.bid.order_id:
            self.user_trade = Consts.BID
        elif trade_obj.ask.order_id:
            self.user_trade = Consts.ASK
        else:
            self.user_trade = u'NO'

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
