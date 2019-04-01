import pyximport; pyximport.install()

import os
import mock
from delorean import Delorean
from cdecimal import Decimal

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money

from algos.naive import Naive
from algos.harness import Harness
from gryphon.lib.models.order import Order
from gryphon.lib.models.exchange import Position, Balance
from algos.base import Strategy
from brain import Brain
from nose.plugins.skip import SkipTest

import logging
logger = logging.getLogger(__name__)

class TestFundamentalValue():

    def setUp(self):
        self.db = mock.Mock()

        exchange = mock.Mock()
        exchange.name = "TEST"
        exchange.friendly_name = "TestExchange"

        other_exchange = mock.Mock()
        other_exchange.name = "COINBASE"
        other_exchange.friendly_name = "OtherExchange"

        params = {
            'max_fiat_balance': "USD 2000"
        }
        self.algo = Strategy(exchange, self.db, params=params)

        self.algo.fundamental_exchanges = [exchange, other_exchange]

        self.harness = Harness(self.algo, self.db)

        self.fundamental_value_map = {
            'TEST':{
                'fiat':Money(1000, 'USD'),
                'btc':Money(10, 'BTC'),
                'fundamental_value': Money(100, 'USD'),
                'bid_quote':Money(99, 'USD'),
                'ask_quote':Money(101, 'USD'),
                'maximum':Money(2000, 'USD')
            },
            'COINBASE':{
                'fiat':Money(1000, 'USD'),
                'btc':Money(10, 'BTC'),
                'fundamental_value': Money(120, 'USD'),
                'bid_quote':Money(119, 'USD'),
                'ask_quote':Money(121, 'USD'),
                'maximum':Money(2000, 'USD')
            }
        }

    def tearDown(self):
        pass

    def test_cfv_equal_capital_equal_maximum(self):
        core_fundamental_value = self.harness.calculate_core_fundamental_value(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("110", "USD"))

    def test_cfv_unequal_capital_equal_maximum(self):
        # the unequal capital should have no effect
        self.fundamental_value_map['TEST'].update({
            'fiat':Money(750, 'USD'),
        })
        self.fundamental_value_map['COINBASE'].update({
            'fiat':Money(1250, 'USD'),
        })

        core_fundamental_value = self.harness.calculate_core_fundamental_value(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("110", "USD"))

    def test_cfv_equal_capital_unequal_maximum(self):
        # should take 110 at weight 1/10 and 120 at weight 9/10 = 119
        self.fundamental_value_map['TEST'].update({
            'maximum':Money(1000, 'USD')
        })
        self.fundamental_value_map['COINBASE'].update({
            'maximum':Money(9000, 'USD')
        })

        core_fundamental_value = self.harness.calculate_core_fundamental_value(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("119", "USD"))

    def test_cfv_low_fiat(self):
        # should ignore TEST's bid_quote since we have no fiat to buy with
        # bid_quote = 119
        # ask_quote = avg(101, 121) = 111
        # cfv = avg(119, 111) = 115
        self.fundamental_value_map['TEST'].update({
            'fiat':Money(0, 'USD'),
        })

        core_fundamental_value = self.harness.calculate_core_fundamental_value(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("115", "USD"))

    def test_cfv_high_fiat(self):
        # should ignore COINBASE's ask_quote since we have max fiat
        # bid_quote = avg(99, 119) = 109
        # ask_quote = 101
        # cfv = avg(109, 101) = 105
        self.fundamental_value_map['COINBASE'].update({
            'fiat':Money(10000, 'USD'),
        })

        core_fundamental_value = self.harness.calculate_core_fundamental_value(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("105", "USD"))

    def test_cfv_low_btc(self):
        # same math as above
        self.fundamental_value_map['COINBASE'].update({
            'btc':Money(1, 'BTC'),
        })

        core_fundamental_value = self.harness.calculate_core_fundamental_value(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("105", "USD"))

    # V2
    def test_cfv_v2_equal_capital_equal_maximum(self):
        core_fundamental_value, __ = self.harness.calculate_core_fundamental_value_v2(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("110", "USD"))

    def test_cfv_v2_low_fiat(self):
        # should ignore TEST entirely since we have no fiat to buy with
        # COINBASE fv = 120
        self.fundamental_value_map['TEST'].update({
            'fiat':Money(0, 'USD'),
        })

        core_fundamental_value, __ = self.harness.calculate_core_fundamental_value_v2(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("120", "USD"))

    def test_cfv_v2_high_fiat(self):
        # should ignore TEST entirely since we have max fiat
        # COINBASE fv = 120
        self.fundamental_value_map['TEST'].update({
            'fiat':Money(10000, 'USD'),
        })

        core_fundamental_value, __ = self.harness.calculate_core_fundamental_value_v2(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("120", "USD"))

    def test_cfv_v2_low_btc(self):
        # should ignore TEST entirely since we have low btc
        # COINBASE fv = 120
        self.fundamental_value_map['TEST'].update({
            'btc':Money(1, 'BTC'),
        })

        core_fundamental_value, __ = self.harness.calculate_core_fundamental_value_v2(self.fundamental_value_map)
        core_fundamental_value.should.equal(Money("120", "USD"))
