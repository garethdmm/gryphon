# -*- coding: utf-8 -*-
import os
from base import Base
import os
import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric, desc
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from gryphon.lib import session
from gryphon.lib.money import Money

metadata = Base.metadata

class MarketDataRetriever(object):
    
    BITSTAMP=u'STMP'
    BTCE=u'BTCE'
    TRADE = u'TRADE'
    XBTUSD = u'XBT/USD'
    
    @staticmethod
    def trades(exchange=BITSTAMP, ticker_symbol=XBTUSD, start_time=datetime.utcnow()-timedelta(days=30), end_time=datetime.utcnow()):
        db = session.get_a_gds_db_mysql_session()
        trades = db.query(MarketData).filter_by(
            exchange=exchange).filter_by(
            ticker_symbol=ticker_symbol).filter_by(
            entry_type=u'TRADE').filter(
            MarketData.timestamp.between(start_time, end_time)).order_by(
            desc(MarketData.timestamp)).all()
        return trades
        

    def orderbook(self):
        pass
     


class MarketData(Base):
    __tablename__ = 'market_data'

    market_data_id = Column(Integer, primary_key=True)
    unique_id = Column(Unicode(64), nullable=False)
    time_added = Column(DateTime, nullable=False)

    timestamp = Column(DateTime, nullable=False)
    exchange = Column(Unicode(256))
    price = Column('price', Numeric(precision=20, scale=10))
    currency = Column(Unicode(256))
    volume = Column('volume', Numeric(precision=20, scale=10))
    entry_type = Column(Unicode(32), nullable=True)
    ticker_symbol = Column(Unicode(256))
    
    def __init__(self, timestamp, exchange, price, currency, volume, entry_type, ticker_symbol):
        self.unique_id = u'mkd_%s' % uuid.uuid4().hex
        self.time_added = datetime.utcnow()

        self.timestamp =timestamp
        self.exchange = exchange
        self.price = price
        self.currency = currency
        self.volume = volume
        self.entry_type = entry_type
        self.ticker_symbol = ticker_symbol
   
    def __str__(self):
        return unicode(self)
 
    def __unicode__(self):
        return '%s,%s,%s,%s,%s,%s,%s' % (
            self.timestamp,
            self.exchange,
            self.price,
            self.currency,
            self.volume,
            self.entry_type,
            self.ticker_symbol,
        )
