# -*- coding: utf-8 -*-
from sqlalchemy import Column, Unicode, UnicodeText

from gryphon.lib.models.base import Base

metadata = Base.metadata

class Flag(Base):
    __tablename__ = 'flag'

    key = Column(Unicode(64), primary_key=True)
    value = Column(UnicodeText(length=2**31))

    def __init__(self, key, value):
        self.key = key
        self.value = value
        
