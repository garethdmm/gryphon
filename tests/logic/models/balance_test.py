"""
This file tests the Balance class, which also tests for us the Position and Target
classes, since they are just clones of Balance.
"""
import pyximport; pyximport.install()

import unittest
import sure

from gryphon.lib.money import Money
from gryphon.lib.models.exchange import Balance


class TestBalance(unittest.TestCase):
    def setUp(self):
        self.balance = Balance({
            'USD': Money("100", "USD"),
            'BTC': Money("1", "BTC")
        })

    def tearDown(self):
        pass

    def test_empty(self):
        balance = Balance()
        balance['BTC'].should.equal(Money("0", "BTC"))

    def test_add_balance(self):
        balance2 = Balance({
            'USD': Money("50", "USD"),
            'BTC': Money("2", "BTC")
        })
        new_balance = self.balance + balance2
        new_balance['USD'].should.equal(Money("150", "USD"))
        new_balance['BTC'].should.equal(Money("3", "BTC"))

    def test_add_money(self):
        new_balance = self.balance + Money("0.2", "BTC")
        new_balance['USD'].should.equal(Money("100", "USD"))
        new_balance['BTC'].should.equal(Money("1.2", "BTC"))

    def test_negate(self):
        neg = -self.balance
        neg['USD'].should.equal(Money("-100", "USD"))
        neg['BTC'].should.equal(Money("-1", "BTC"))

    def test_fiat(self):
        fiat = self.balance.fiat()
        fiat.should.equal(Money("100", "USD"))

    def test_add_result_mutability(self):
        m = Money(2, 'BTC')
        new_balance = self.balance + m #  => USD 100, BTC 3
        new_balance['USD'].should.equal(Money("100", "USD"))

        self.balance['USD'].amount += 10 # USD 110

        # Changing self.balance shouldn't affect new_balance
        new_balance['USD'].should.equal(Money("100", "USD"))
