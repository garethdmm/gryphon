# -*- coding: utf-8 -*-
import os
from gryphon.lib.models.emeraldhavoc.base import EmeraldHavocBase
import json
import uuid
from decimal import *
from collections import defaultdict

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_factory import make_exchange_from_key
from gryphon.lib import gryphon_json_serialize
from datetime import datetime, date, timedelta
from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

metadata = EmeraldHavocBase.metadata

class Orderbook(EmeraldHavocBase):
    __tablename__ = 'orderbook'
    
    orderbook_id = Column(Integer, primary_key=True)
    unique_id = Column(Unicode(64), nullable=False)
    exchange = Column(Unicode(64), nullable=False)
    timestamp = Column(DateTime, nullable=True)
    time_created = Column(DateTime, nullable=False)
    _bids = Column('bids', UnicodeText(length=2**31))
    _asks = Column('asks', UnicodeText(length=2**31))
    
    def __init__(self, exchange, orderbook, timestamp=None):
        self.unique_id = unicode(uuid.uuid4().hex)
        self.time_created = datetime.utcnow()
        self.timestamp = timestamp
        self.bids = orderbook['bids']
        self.asks = orderbook['asks']
        self.exchange = exchange
        
    def __unicode__(self):
        bids = self.bids[:5]
        asks = self.asks[:5]
        output = u"\n%s\nBids\n" % self.exchange
        output += u"{0:15} | {1:15}\n".format("Price", "Amount")
        for bid in bids:
            output += u"{0:15} | {1:15}\n".format(bid[0], bid[1])

        output += u"Asks\n"
        output += u"{0:15} | {1:15}\n".format("Price", "Amount")

        for ask in asks:
            output += u"{0:15} | {1:15}\n".format(ask[0], ask[1])
        
        return output
        
    def __repr__(self):
        return self.to_json()
    
    def to_json(self):
        return json.dumps({
            'trade_id':self.trade_id,
            'time_created':unicode(self.time_created),
            'unique_id':self.unique_id,
            'exchange':self.exchange,
            'bids':self.bids,
            'asks':self.asks
        }, ensure_ascii=False)
    
    @property
    def bids(self):
        return json.loads(self._bids)

    @bids.setter
    def bids(self, value):
        self._bids = json.dumps(value, ensure_ascii=False)

    @property
    def asks(self):
        return json.loads(self._asks)

    @asks.setter
    def asks(self, value):
        self._asks = json.dumps(value, ensure_ascii=False)


