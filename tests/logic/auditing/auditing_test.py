"""
Tests for gryphon.execution.auditing.
"""

import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import unittest
import sure

from gryphon.execution.lib import auditing
from gryphon.lib.money import Money
from gryphon.lib.models.exchange import Balance


class TestAuditing(unittest.TestCase):
    def test_trivial(self):
        db_balance = Balance()
        ledger_balance = Balance()

        auditing.balance_equality(db_balance, ledger_balance).should.equal(True)

    def test_symmetric_equal(self):
        db_balance = Balance({'USD': Money('50', 'USD'), 'BTC': Money('0', 'BTC')})
        ledger_balance = Balance({'USD': Money('50', 'USD'), 'BTC': Money('0', 'BTC')})

        auditing.balance_equality(db_balance, ledger_balance).should.equal(True)

    def test_symmetric_not_equal(self):
        db_balance = Balance({'USD': Money('50', 'USD'), 'BTC': Money('0', 'BTC')})
        ledger_balance = Balance({'USD': Money('51', 'USD'), 'BTC': Money('0', 'BTC')})

        auditing.balance_equality(db_balance, ledger_balance).should.equal(False)

    def test_symmetric_very_not_equal(self):
        db_balance = Balance({'USD': Money('50', 'USD'), 'BTC': Money('0', 'BTC')})

        ledger_balance = Balance({
            'USD': Money('-60', 'USD'),
            'BTC': Money('100', 'BTC'),
        })

        auditing.balance_equality(db_balance, ledger_balance).should.equal(False)

    def test_complex_symmetric_equal(self):
        db_balance = Balance({
            'USD': Money('50', 'USD'),
            'CAD': Money('10000', 'CAD'),
            'ETH': Money('0', 'ETH'),
            'BTC': Money('0', 'BTC'),
        })

        ledger_balance = Balance({
            'USD': Money('50', 'USD'),
            'CAD': Money('10000', 'CAD'),
            'ETH': Money('0', 'ETH'),
            'BTC': Money('0', 'BTC'),
        })

        auditing.balance_equality(db_balance, ledger_balance).should.equal(True)

    def test_complex_symmetric_not_equal(self):
        db_balance = Balance({
            'USD': Money('50', 'USD'),
            'CAD': Money('10000', 'CAD'),
            'ETH': Money('0', 'ETH'),
            'BTC': Money('0', 'BTC'),
        })

        ledger_balance = Balance({
            'USD': Money('50', 'USD'),
            'CAD': Money('10000', 'CAD'),
            'ETH': Money('-1000', 'ETH'),
            'BTC': Money('-5000', 'BTC'),
        })

        auditing.balance_equality(db_balance, ledger_balance).should.equal(False)

    def test_asymmetric_equal(self):
        db_balance = Balance({'USD': Money('50', 'USD'), 'BTC': Money('0', 'BTC')})
        ledger_balance = Balance({'USD': Money('50', 'USD')})

        auditing.balance_equality(db_balance, ledger_balance).should.equal(True)

    def test_asymmetric_not_equal(self):
        db_balance = Balance({'USD': Money('50', 'USD'), 'BTC': Money('0', 'BTC')})
        ledger_balance = Balance({'USD': Money('51', 'USD')})

        auditing.balance_equality(db_balance, ledger_balance).should.equal(False)

    def test_asymmetric_very_not_equal(self):
        db_balance = Balance({'USD': Money('50', 'USD'), 'BTC': Money('0', 'BTC')})
        ledger_balance = Balance({'USD': Money('-10000', 'USD')})

        auditing.balance_equality(db_balance, ledger_balance).should.equal(False)

    def test_complex_asymmetric_equal(self):
        db_balance = Balance({
            'USD': Money('50', 'USD'),
            'CAD': Money('10000', 'CAD'),
            'ETH': Money('0', 'ETH'),
            'BTC': Money('0', 'BTC'),
        })

        ledger_balance = Balance({
            'USD': Money('50', 'USD'),
            'CAD': Money('10000', 'CAD'),
        })

        auditing.balance_equality(db_balance, ledger_balance).should.equal(True)

    def test_complex_asymmetric_not_equal(self):
        db_balance = Balance({
            'USD': Money('50', 'USD'),
            'CAD': Money('10000', 'CAD'),
            'ETH': Money('0', 'ETH'),
            'BTC': Money('0', 'BTC'),
        })

        ledger_balance = Balance({
            'USD': Money('50', 'USD'),
            'CAD': Money('-10000', 'CAD'),
        })

        auditing.balance_equality(db_balance, ledger_balance).should.equal(False)


