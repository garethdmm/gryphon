import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import os
import unittest
import sure
import mock
from mock import patch
from decimal import Decimal

from gryphon.lib.money import Money
from gryphon.lib.test_helper import *

import logging
logger = logging.getLogger(__name__)

# the money model we base ours on (https://github.com/carlospalol/money)
# has good tests, so we only need to test the specific features we have added

class TestMoney():
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_invalid_currency(self):
        Money.when.called_with("100", "XXX").should.throw(ValueError)

    def test_currency_conversion_to_same_currency(self):
        m = Money(100, "USD")
        m.to("USD").should.equal(m)

    # we have to be careful here to not cache bad data in memcache
    @patch('gryphon.lib.forex.USDCurrencyConverter')
    def test_currency_conversion(self, patched_currency_converter):
        patched_currency_converter._all_rates = mock.Mock(return_value={'USD': 1, 'CAD': Decimal("2")})

        m = Money(100, "CAD")
        expected_usd = Money(50, "USD")
        m.to("USD").should.equal(expected_usd)

    def test_currency_conversion_passing_exchange_rate(self):
        m = Money(100, "CAD")
        rate_to_usd = Decimal("0.8") # ouch
        expected_usd = Money(80, "USD")
        m.to("USD", exchange_rate_to_usd=rate_to_usd).should.equal(expected_usd)

    def test_thousands_commas_in_numbers(self):
        m_as_int = Money(1000, "USD")

        m_with_commas = Money("1,000", "USD")
        m_with_commas.should.equal(m_as_int)

        m_with_commas_loads = Money.loads("USD 1,000")
        m_with_commas_loads.should.equal(m_as_int)

    def test_round_to_decimal_places(self):
        m = Money('5.12345678', 'BTC')
        rounded_to_4 = Money('5.1235', 'BTC')
        rounded_to_2 = Money('5.13', 'BTC')

        m.round_to_decimal_places(4).should.equal(rounded_to_4)
        m.round_to_decimal_places(2).should.equal(rounded_to_2)
        m.round_to_decimal_places(8).should.equal(m)

    def test_round_to_bucket(self):
        m = Money('3223.45', 'USD')
        rounded_to_100 = Money('3200', 'USD')
        rounded_to_1000 = Money('3000', 'USD')

        m.round_to_bucket(100).should.equal(rounded_to_100)
        m.round_to_bucket(1000).should.equal(rounded_to_1000)
        m.round_to_bucket(Decimal('0.01')).should.equal(m)
