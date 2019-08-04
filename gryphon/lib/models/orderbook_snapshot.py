# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
from .base import Base
import json
import uuid
from datetime import datetime
from six import text_type
from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, BigInteger, Numeric

metadata = Base.metadata

class OrderbookSnapshot(Base):
    __tablename__ = 'orderbook_snapshot'

    unique_id = Column(Unicode(64), nullable=False)
    orderbook_id = Column(Integer, primary_key=True)
    data = Column(UnicodeText(length=2**31))
    time_retrieved = Column(DateTime, nullable=False)

    def __init__(self, data, time_retrieved):
        self.unique_id = u'ord_%s' % text_type(uuid.uuid4().hex)
        self.time_retrieved = time_retrieved
        self.data = data

    def __unicode__(self):
        return u'Orderbook_Snapshot'

    def __repr__(self):
        return json.dumps({
            'data': self.data,
            'time_retrieved': text_type(self.time_retrieved),
        }, ensure_ascii=False)
