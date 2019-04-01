# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import datetime, date, timedelta
import json
import os
import requests
import uuid

from decimal import *
from delorean import Delorean
from sqlalchemy import ForeignKey, Column, Integer, Unicode, DateTime, UnicodeText, Numeric
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import and_, func

from gryphon.lib import gryphon_json_serialize
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_factory import make_exchange_from_key
from gryphon.lib.logger import get_logger
from gryphon.lib.models.base import Base
from gryphon.lib.money import Money
from gryphon.lib.util.list import flatten

logger = get_logger(__name__)

metadata = Base.metadata


class Transaction(Base):
    __tablename__ = 'transaction'
    
    #Transaction Types
    WITHDRAWL = 'WITHDRAWL'
    DEPOSIT = 'DEPOSIT'
    
    #Transaction Status'
    IN_TRANSIT = 'IN_TRANSIT'
    COMPLETED = 'COMPLETED'
    CANCELED = 'CANCELED'
    
    transaction_id = Column(Integer, primary_key=True)
    transaction_type = Column(Unicode(64))
    transaction_status = Column(Unicode(64))
    unique_id = Column(Unicode(64), nullable=False)
    time_created = Column(DateTime, nullable=False)
    time_completed = Column(DateTime, nullable=True)
    
    _amount = Column('amount', Numeric(precision=24, scale=14))
    _amount_currency = Column('amount_currency', Unicode(3))
    _fee = Column('fee', Numeric(precision=24, scale=14))
    _fee_currency = Column('fee_currency', Unicode(3))
    _transaction_details = Column('transaction_details', UnicodeText(length=2**31))
    
    exchange_id = Column(Integer, ForeignKey('exchange.exchange_id'))

    # Some Transactions have BTC fees, which reduce our total BTC assets. Every once in a while
    # we create a "buyback" transaction where we buy back those fees outside our trading system.
    # We then mark the fee as "bought back" by setting the transaction's fee_buyback_transaction
    # This one is a bit complex because it is self-referential
    fee_buyback_transaction_id = Column(Integer, ForeignKey('transaction.transaction_id'))
    fee_buyback_transaction = relationship("Transaction", remote_side=[transaction_id], backref='fee_buyback_transactions')
    
    def __init__(self, transaction_type, transaction_status, amount, exchange, transaction_details, fee=None):
        self.unique_id = unicode(uuid.uuid4().hex)
        self.time_created = datetime.utcnow()
        self.transaction_type = transaction_type
        self.transaction_status = transaction_status
        self.amount = amount
        self.exchange = exchange
        self.transaction_details = transaction_details
        if fee:
            self.fee = fee
        
    def __unicode__(self):
        return u'[TRANSACTION:%s, EXCHANGE:%s, STATUS:%s] Amount:%s (%s) at %s' % (
            self.transaction_type, self.exchange.name, self.transaction_status, self.amount, self.fee, self.time_created)
        
    def __repr__(self):
        return self.to_json()
    
    def to_json(self):
        return json.dumps({
            'transaction_id':self.transaction_id,
            'transaction_type':self.transaction_type,
            'transaction_status':self.transaction_status,
            'time_created':unicode(self.time_created),
            'unique_id':self.unique_id,
            'exchange':self.exchange.name,
            'amount':self.amount,
            'fee': self.fee,
            'transaction_details':self.transaction_details
        }, ensure_ascii=False)
    
    @property
    def transaction_details(self):
        return json.loads(self._transaction_details)

    @transaction_details.setter
    def transaction_details(self, value):
        self._transaction_details = json.dumps(value, ensure_ascii=False)
    
    @property
    def amount(self):
        return Money(self._amount, self._amount_currency)

    @amount.setter
    def amount(self, value):
        self._amount = value.amount
        self._amount_currency = value.currency

    @property
    def fee(self):
        if self._fee and self._fee_currency:
            return Money(self._fee, self._fee_currency)
        else:
            return None

    @fee.setter
    def fee(self, value):
        self._fee = value.amount
        self._fee_currency = value.currency

    @hybrid_property
    def has_outstanding_btc_fee(self):
        return self._fee_currency == 'BTC' and self.fee_buyback_transaction_id == None and self.transaction_status != self.CANCELED

    @has_outstanding_btc_fee.expression
    def has_outstanding_btc_fee(cls):
        return and_(cls._fee_currency == 'BTC', cls.fee_buyback_transaction_id == None, cls.transaction_status != cls.CANCELED)

    def complete(self):
        if self.transaction_status != self.IN_TRANSIT:
            raise ValueError("We can only complete an IN_TRANSIT transaction")
        self.transaction_status = self.COMPLETED
        self.time_completed = datetime.utcnow()

        if self.transaction_type == self.DEPOSIT:
            self.exchange.balance[self.amount.currency] += self.amount
        elif self.transaction_type == self.WITHDRAWL:
            self.exchange.balance[self.amount.currency] -= self.amount

        if self.fee:
            self.exchange.balance[self.fee.currency] -= self.fee

    def cancel(self):
        if self.transaction_status == self.IN_TRANSIT:
            self.transaction_status = self.CANCELED
        elif self.transaction_status == self.COMPLETED:
            self.transaction_status = self.CANCELED

            if self.transaction_type == self.DEPOSIT:
                self.exchange.balance[self.amount.currency] -= self.amount
            elif self.transaction_type == self.WITHDRAWL:
                self.exchange.balance[self.amount.currency] += self.amount

            if self.fee:
                self.exchange.balance[self.fee.currency] += self.fee
        else:
            raise ValueError("We can only cancel an IN_TRANSIT or COMPLETED transaction")

    def confirmations(self):
        if self.transaction_details and 'transaction_hash' in self.transaction_details:
            r = requests.get('https://api.blockcypher.com/v1/btc/main/txs/%s' % self.transaction_details['transaction_hash'])
            response = r.json()
            if 'confirmations' in response:
                return int(response['confirmations'])

        return None

    def already_has_tx_hash(self):
        return (self.transaction_details and
            'transaction_hash' in self.transaction_details and
            self.transaction_details['transaction_hash'])

    def can_lookup_tx_hash(self):
        return (self.amount.currency == "BTC" and
            self.transaction_details and
            'deposit_address' in self.transaction_details)

    def update_tx_hash(self):
        if not self.already_has_tx_hash() and self.can_lookup_tx_hash():
            tx_hash = self.find_on_blockchain()
            logger.info("Found %s %s on the blockchain: %s" % (self.exchange.name, self.amount, tx_hash))

            # can't directly update self.transaction_details because it is a json magic field
            tx_details = self.transaction_details
            tx_details['transaction_hash'] = tx_hash
            self.transaction_details = tx_details

    def find_on_blockchain(self):
        deposit_address = self.transaction_details['deposit_address']
        satoshi_amount = int(self.amount * 10**8)

        r = requests.get('https://api.blockcypher.com/v1/btc/main/addrs/%s/full' % deposit_address)
        response = r.json()
        transactions = response['txs']

        for transaction in transactions:
            for output in transaction['outputs']:
                if deposit_address in output['addresses'] and output['value'] == satoshi_amount:
                    return transaction['hash']

        return None

    # a transaction is stuck if it has been in transit for more than 3 hours
    def is_stuck(self):
        return self.amount.currency == "BTC" and \
            self.transaction_status == self.IN_TRANSIT and \
            Delorean(self.time_created, "UTC") < Delorean().last_hour(3)

    @property
    def position(self):
        from gryphon.lib.models.exchange import Position
        position = Position()
        if self.transaction_type == self.DEPOSIT:
            position[self.amount.currency] += self.amount
        elif self.transaction_type == self.WITHDRAWL:
            position[self.amount.currency] -= self.amount
        if self.fee:
            position[self.fee.currency] -= self.fee
        return position

    @hybrid_property
    def magic_time_completed(self):
        """
        Regular property you can call on a loaded trade in python. Returns a USD Money object
        """
        if self.time_completed:
            return self.time_completed
        else:
            return self.time_created

    @magic_time_completed.expression
    def magic_time_completed(cls):
        """
        SQL Expression which lets us calculate and use USD prices in SQL.

        Must have Order joined in queries where it is used.
        Ex: db.query(func.sum(Trade.price_in_usd)).join(Order).scalar()
        This gives decimal results, since we don't have our Money objects in SQL
        """
        return func.IF(cls.time_completed, cls.time_completed, cls.time_created)
