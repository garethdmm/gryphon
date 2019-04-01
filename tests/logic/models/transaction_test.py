import pyximport; pyximport.install()

import os
import unittest
import sure
from mock import patch

from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.models.exchange import Exchange, Position
from gryphon.lib.models.transaction import Transaction

import logging
logger = logging.getLogger(__name__)

class TestTransaction():
    def mockExchange(self, name=None):
        exchange_name = "TEST"
        if name:
            exchange_name += ("_" + name)
        exchange = Exchange(exchange_name)
        exchange.currency = "USD"
        return exchange

    def setUp(self):
        amount = Money(1, "BTC")

        self.source_exchange = self.mockExchange("SOURCE")
        self.target_exchange = self.mockExchange("TARGET")

        self.deposit = Transaction(Transaction.DEPOSIT, Transaction.IN_TRANSIT, amount, self.target_exchange, {})
        self.withdrawal = Transaction(Transaction.WITHDRAWL, Transaction.IN_TRANSIT, amount, self.source_exchange, {})

    def tearDown(self):
        pass

    def test_withdrawal(self):
        old_balance = self.source_exchange.balance['BTC']
        self.withdrawal.complete()
        new_balance = self.source_exchange.balance['BTC']
        balance_delta = new_balance - old_balance
        balance_delta.should.equal(Money.loads("BTC -1"))

    def test_deposit(self):
        old_balance = self.target_exchange.balance['BTC']
        self.deposit.complete()
        new_balance = self.target_exchange.balance['BTC']
        balance_delta = new_balance - old_balance
        balance_delta.should.equal(Money.loads("BTC 1"))

    def test_withdrawal_fee(self):
        self.withdrawal.fee = Money.loads("BTC 0.1")
        old_balance = self.source_exchange.balance['BTC']
        self.withdrawal.complete()
        new_balance = self.source_exchange.balance['BTC']
        balance_delta = new_balance - old_balance
        balance_delta.should.equal(Money.loads("BTC -1.1"))

    def test_deposit_fee(self):
        self.deposit.fee = Money.loads("BTC 0.1")
        old_balance = self.target_exchange.balance['BTC']
        self.deposit.complete()
        new_balance = self.target_exchange.balance['BTC']
        balance_delta = new_balance - old_balance
        balance_delta.should.equal(Money.loads("BTC 0.9"))

    def test_withdrawal_completed_cancel(self):
        self.withdrawal.fee = Money.loads("BTC 0.1")
        old_balance = self.source_exchange.balance['BTC']
        self.withdrawal.complete()
        self.withdrawal.cancel()
        new_balance = self.target_exchange.balance['BTC']
        new_balance.should.equal(old_balance)

    def test_deposit_completed_cancel(self):
        self.deposit.fee = Money.loads("BTC 0.1")
        old_balance = self.source_exchange.balance['BTC']
        self.deposit.complete()
        self.deposit.cancel()
        new_balance = self.target_exchange.balance['BTC']
        new_balance.should.equal(old_balance)

    def test_withdrawal_in_transit_cancel(self):
        old_balance = self.source_exchange.balance['BTC']
        self.withdrawal.cancel()
        self.withdrawal.transaction_status.should.equal(Transaction.CANCELED)
        new_balance = self.target_exchange.balance['BTC']
        new_balance.should.equal(old_balance)

    def test_double_complete(self):
        self.withdrawal.complete()
        self.withdrawal.complete.when.called_with().should.throw(ValueError)

    def test_double_cancel(self):
        self.withdrawal.cancel()
        self.withdrawal.cancel.when.called_with().should.throw(ValueError)
