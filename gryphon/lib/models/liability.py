# -*- coding: utf-8 -*-
"""
This class is used to represent liabilities against the business or fund. It is used
extensively in gryphon.lib.assets to give a correct picture of the business's
financial position.

TODO:
  - Implement functions to calculate the current repayable value of a liability, be it
    a loan or a fund investment.
  - the current implementation of self.details, self.interest_rate,
    self.compounding_period, is really just a demonstraction. It should be re-
    implemented in the style of the balance column in the exchange account model.
"""
from datetime import datetime
import json
import uuid

from cdecimal import Decimal
from delorean import Delorean
from sqlalchemy import Column, Integer, Unicode, DateTime, UnicodeText, Numeric

from gryphon.lib.logger import get_logger
from gryphon.lib.models.base import Base
from gryphon.lib.money import Money

logger = get_logger(__name__)

metadata = Base.metadata


UNICODE_STRING_REP = """\
[LIABILITY: %s to %s of type %s started %s and repayed %s]\
"""

class Liability(Base):
    __tablename__ = 'liability'

    # Liability types.
    FIXED_INTEREST = 'FIXED_INTEREST'  # Fixed interest loans or similar.
    PERFORMANCE = 'PERFORMANCE'  # Fund investments.

    # Columns.
    # Meta-columns.
    liability_id = Column(Integer, primary_key=True)
    unique_id = Column(Unicode(64), nullable=False)
    time_created = Column(DateTime, nullable=False)

    # Data columns.
    _amount = Column('amount', Numeric(precision=24, scale=14))
    _amount_currency = Column('amount_currency', Unicode(3))
    liability_type = Column(Unicode(64))
    entity_name = Column(Unicode(128), nullable=False)
    time_started = Column(DateTime, nullable=True)
    time_repayed = Column(DateTime, nullable=True)
    _details = Column('details', UnicodeText(length=2**31))

    def __init__(self, amount, liability_type, entity_name, time_started=None, time_repayed=None, details=None):
        self.unique_id = unicode(uuid.uuid4().hex)
        self.time_created = datetime.utcnow()

        self.amount = amount
        self.liability_type = liability_type
        self.entity_name = entity_name
        self.time_started = time_started
        self.time_repayed = time_repayed
        self.details = details

    def __str__(self):
        return UNICODE_STRING_REP % (
            self.amount,
            self.entity_name,
            self.liability_type,
            self.time_started if self.time_started else '[NOT STARTED]',
            self.time_repayed if self.time_repayed else '[NOT REPAYED]',
        )

    def __repr__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps({
            'liability_id': self.liability_id,
            'unique_id': self.unique_id,
            'time_created': unicode(self.time_created),
            'amount': self.amount,
            'liability_type': self.liability_type,
            'entity_name': self.entity_name,
            'time_started': unicode(self.time_started),
            'time_repayed': unicode(self.time_repayed),
            'details': self.details,
        }, ensure_ascii=False)

    @property
    def details(self):
        if self._details != 'null':
            return json.loads(self._details)
        else:
            return {}

    @details.setter
    def details(self, value):
        self._details = json.dumps(value, ensure_ascii=False)

    @property
    def amount(self):
        return Money(self._amount, self._amount_currency)

    @amount.setter
    def amount(self, value):
        self._amount = value.amount
        self._amount_currency = value.currency

    def start(self):
        self.time_started = Delorean().datetime

    def complete(self):
        self.time_repayed = Delorean().datetime

    @property
    def interest_rate(self):
        if 'interest_rate' in self.details:
            return Decimal(str(self.details['interest_rate']))
        else:
            return Decimal('0')

    @interest_rate.setter
    def interest_rate(self, value):
        """
        We might save some code (or duplication) if we used something like the
        JSONEncodedMoneyDict from the exchange model here, but this works for now, and
        this table is expected to be small so this shouldn't affect performance.
        """
        new_details = self.details
        new_details['interest_rate'] = float(value)
        self.details = new_details

    @property
    def compounding_period(self):
        """
        We track the compounding period of fixed-interest debts as an integer number
        of months.
        """
        if 'compounding_period' in self.details:
            return Decimal(str(self.details['compounding_period']))
        else:
            return Decimal('0')

    @compounding_period.setter
    def compounding_period(self, value):
        new_details = self.details
        new_details['compounding_period'] = float(value)
        self.details = new_details

