# -*- coding: utf-8 -*-
from datetime import datetime
import json
import os
import uuid

from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, BigInteger, Numeric

from gryphon.lib.models.base import Base
from gryphon.lib.session import commit_mysql_session
from gryphon.lib.singleton import Singleton

metadata = Base.metadata


class Event(Base):
    __tablename__ = 'event'
   
    unique_id = Column(Unicode(64), nullable=False)
    event_id = Column(Integer, primary_key=True)
    time_created = Column(DateTime, nullable=False)
    exchange_name = Column(Unicode(256), nullable=False)
    event_type = Column(Unicode(256), nullable=False)
    data = Column(UnicodeText(length=2**31))
 
    def __init__(self, event_type, exchange_name, data):
        self.time_created = datetime.utcnow()
        self.event_type = event_type
        self.exchange_name = exchange_name
        self.unique_id = u'evt_%s' % unicode(uuid.uuid4().hex)
        self.data = json.dumps(data)
        
    def __unicode__(self):
        return unicode(repr(self))
        
    def __repr__(self):
        return json.dumps({
            'event_type':self.event_type,
            'exchange':self.exchange_name,
            'data': json.loads(self.data),
            'time_created': unicode(self.time_created),
        }, ensure_ascii=False)


class EventRecorder(object):
    __metaclass__ = Singleton

    def create(self, db=None, logger=None):
        self.db = db
        self.external_logger = logger
        
    def record(self, event_type, exchange_name='', data={}):
        event = Event(event_type, exchange_name, data)
        
        if not hasattr(self, 'db') and not hasattr(self, 'external_logger'):
            # we didn't call create. we aren't recording events
            return
        
        if self.db:
            self.db.add(event)
            commit_mysql_session(self.db)
        elif self.external_logger:
            self.external_logger.info('[EVENT] %s : %s : %s -- %s' % (event.exchange_name, event.event_type, str(event.time_created), json.dumps(event.data)))
        else:
            # we aren't recording events.
            pass
            

                
