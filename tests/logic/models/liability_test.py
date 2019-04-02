import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import os
import unittest
import sure
import mock
from decimal import Decimal
from delorean import Delorean

from gryphon.lib.models.liability import Liability
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse


class TestLiability(unittest.TestCase):
    def setUp(self):
        self.basic_liability = Liability(
            Money('100', 'ETH'),
            Liability.FIXED_INTEREST,
            'John',
        )

    def tearDown(self):
        pass

    def test_creation(self):
        l = self.basic_liability

        l.time_started.should.equal(None)
        l.time_repayed.should.equal(None)
        l.amount.should.equal(Money('100', 'ETH'))
        l.entity_name.should.equal('John')

    def test_creation_with_times(self):
        l = Liability(
                Money('100', 'ETH'),
                Liability.FIXED_INTEREST,
                'John',
                time_started=parse('2016-10-1').datetime,
                time_repayed=parse('2016-11-1').datetime,
        )

        l.time_started.should.equal(parse('2016-10-1').datetime)
        l.time_repayed.should.equal(parse('2016-11-1').datetime)
        l.amount.should.equal(Money('100', 'ETH'))
        l.entity_name.should.equal('John')

    def test_start(self):
        l = self.basic_liability

        l.start()

        l.time_started.day.should.equal(Delorean().datetime.day)
        l.time_repayed.should.equal(None)

    def test_end(self):
        l = self.basic_liability

        l.start()
        l.complete()

        l.time_started.day.should.equal(Delorean().datetime.day)
        l.time_repayed.day.should.equal(Delorean().datetime.day)

    def test_creation_with_details(self):
        l = Liability(
                Money('100', 'ETH'),
                Liability.FIXED_INTEREST,
                'John',
                time_started=parse('2016-10-1').datetime,
                details={'interest_rate': 0.05},
        )

        l.details['interest_rate'].should.equal(0.05)

    def test_interest(self):
        l = self.basic_liability

        l.interest_rate = Decimal('0.01')

        l.interest_rate.should.equal(Decimal('0.01'))

    def test_compounding(self):
        l = self.basic_liability

        l.compounding_period = Decimal('12')

        l.compounding_period.should.equal(Decimal('12'))
