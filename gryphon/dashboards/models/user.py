# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
import logging

from sqlalchemy import Column, Integer, Unicode, DateTime

from gryphon.dashboards.models.base import Base
from gryphon.dashboards.models.columns.password_column import PasswordColumn

metadata = Base.metadata
logger = logging.getLogger(__name__)


class User(Base):
    __tablename__ = 'user'

    ADMIN_TYPE = 'ADMIN'

    user_id = Column(Integer, primary_key=True)
    unique_id = Column(Unicode(64), nullable=False)
    username = Column(Unicode(64), nullable=False)
    password = Column(PasswordColumn, nullable=False)
    user_type = Column(Unicode(64), nullable=False)
    time_created = Column(DateTime, nullable=False)

    def __init__(self, username, password):
        self.unique_id = uuid.uuid4().hex
        self.time_created = datetime.now()
        self.user_type = User.ADMIN_TYPE
        self.username = username
        # Must be a Password object from models.columns.password_column
        self.password = password
