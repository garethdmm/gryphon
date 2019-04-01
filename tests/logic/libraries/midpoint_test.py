import pyximport; pyximport.install()

import os
import unittest
import sure

from cdecimal import Decimal

from gryphon.lib.metrics import midpoint
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.money import Money
from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange

class TestMidpoint(unittest.TestCase):
    def setUp(self):
        self.empty_book = {
            'bids': [],
            'asks': [],
        }

        self.exchange = CoinbaseBTCUSDExchange()

    def basic_book(self,price_currency='USD', vol_currency='BTC'):
        def price(val):
            return Money(val, price_currency)

        def vol(val):
            return Money(val, vol_currency)

        bids = [Order(price('249'), vol('10'), self.exchange, Order.BID)]
        asks = [Order(price('251'), vol('10'), self.exchange, Order.ASK)]

        return {'bids': bids, 'asks': asks}

    def bigger_book(self, price_currency='USD', vol_currency='BTC'):
        def price(value):
            return Money(value, price_currency)

        def vol(value):
            return Money(value, vol_currency)

        bids = [
            Order(price('249'), vol('10'), self.exchange, Order.BID),
            Order(price('248'), vol('10'), self.exchange, Order.BID)
        ]

        asks = [
            Order(price('251'), vol('10'), self.exchange, Order.ASK),
            Order(price('260'), vol('10'), self.exchange, Order.ASK),
        ]

        return {'bids': bids, 'asks': asks}

    def test_empty(self):
        midpoint.get_midpoint_from_orderbook.when.called_with(self.empty_book)\
            .should.throw(midpoint.OrderbookSizeException)

    def test_basic(self):
        result = midpoint.get_midpoint_from_orderbook(self.basic_book())
        result.should.equal(Money('250', 'USD'))

    def test_basic_non_btc(self):
        result = midpoint.get_midpoint_from_orderbook(
            self.basic_book(vol_currency='ETH'),
        )

        result.should.equal(Money('250', 'USD'))

    def test_basic_crypto_crypto(self):
        result = midpoint.get_midpoint_from_orderbook(
            self.basic_book(price_currency='BTC', vol_currency='ETH'),
        )

        result.should.equal(Money('250', 'BTC'))

    def test_basic_with_depth(self):
        result = midpoint.get_midpoint_from_orderbook(
            self.basic_book(price_currency='BTC', vol_currency='ETH'),
            depth=Money('0.5', 'ETH'),
        )

        result.should.equal(Money('250', 'BTC'))

    def test_basic_with_bad_depth(self):
        result = midpoint.get_midpoint_from_orderbook.when.called_with(
            self.basic_book(price_currency='BTC', vol_currency='ETH'),
            depth=Money('0.5', 'BTC'),
        ).should.throw(midpoint.OrderbookSizeException)

    def test_bigger(self):
        result = midpoint.get_midpoint_from_orderbook(self.basic_book())
        result.should.equal(Money('250', 'USD'))

    def test_bigger_with_depth(self):
        result = midpoint.get_midpoint_from_orderbook(
            self.bigger_book(),
            depth=Money('20', 'BTC'),
        )

        result.should.equal(Money('252', 'USD'))
