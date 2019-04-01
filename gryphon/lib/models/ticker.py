# -*- coding: utf-8 -*-
from datetime import datetime
import json
import os
import uuid

from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, BigInteger, Numeric

from gryphon.lib.models.base import Base

metadata = Base.metadata


class Ticker(Base):
    __tablename__ = 'ticker'
   
    unique_id = Column(Unicode(64), nullable=False)
    ticker_id = Column(Integer, primary_key=True)
    exchange = Column(Unicode(256))
    data = Column(UnicodeText(length=2**31))
    time_retrieved = Column(DateTime, nullable=False)
 
    def __init__(self, exchange, data):
        self.time_retrieved = datetime.utcnow()
        self.exchange = exchange
        self.unique_id = u'tkr_%s' % unicode(uuid.uuid4().hex)
        self.data = json.dumps(data)
        
    def __unicode__(self):
        return unicode(repr(self))
        
    def __repr__(self):
        return json.dumps({
            'exchange':self.exchange,
            'data': self.data,
            'time_retrieved': unicode(self.time_retrieved),
        }, ensure_ascii=False)
