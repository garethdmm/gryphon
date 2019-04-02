import pyximport; pyximport.install()

import os
import unittest
import sure

from cdecimal import Decimal

from gryphon.lib import market_making
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.money import Money
from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange


class TestMarketMaking(unittest.TestCase):
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

    def test_fixed_spread_basic(self):
        result = market_making.midpoint_centered_fixed_spread(
            self.basic_book(),
            Decimal('0.01'),
        )

        result[0].should.equal(Money('247.5', 'USD'))
        result[1].should.equal(Money('252.5', 'USD'))

    def test_fixed_spread_thin(self):
        result = market_making.midpoint_centered_fixed_spread(
            self.basic_book(),
            Decimal('0.0001'),
        )

        result[0].should.equal(Money('249.975', 'USD'))
        result[1].should.equal(Money('250.025', 'USD'))

    def test_fixed_spread_wide(self):
        result = market_making.midpoint_centered_fixed_spread(
            self.basic_book(),
            Decimal('0.5'),
        )

        result[0].should.equal(Money('125', 'USD'))
        result[1].should.equal(Money('375', 'USD'))

    def test_fixed_spread_crypto_price(self):
        result = market_making.midpoint_centered_fixed_spread(
            self.basic_book(price_currency='BTC', vol_currency='ETH'),
            Decimal('0.0001'),
        )

        result[0].should.equal(Money('249.975', 'BTC'))
        result[1].should.equal(Money('250.025', 'BTC'))

    def test_fixed_spread_crypto_price_quote_depth(self):
        result = market_making.midpoint_centered_fixed_spread(
            self.bigger_book(price_currency='BTC', vol_currency='ETH'),
            Decimal('0.0001'),
            quote_depth=Money('20', 'ETH'),
        )

        result[0].should.equal(Money('251.9748', 'BTC'))
        result[1].should.equal(Money('252.0252', 'BTC'))

    def test_no_position(self):
        result = market_making.simple_position_responsive_sizing(
            Money('2', 'BTC'),
            Money('0', 'BTC'),
        )

        result[0].should.equal(Money('2', 'BTC'))
        result[1].should.equal(Money('2', 'BTC'))

    def test_long_position(self):
        result = market_making.simple_position_responsive_sizing(
            Money('2', 'BTC'),
            Money('1', 'BTC'),
        )

        result[0].should.equal(Money('1', 'BTC'))
        result[1].should.equal(Money('2', 'BTC'))

    def test_short_position(self):
        result = market_making.simple_position_responsive_sizing(
            Money('2', 'BTC'),
            Money('-1', 'BTC'),
        )

        result[0].should.equal(Money('2', 'BTC'))
        result[1].should.equal(Money('1', 'BTC'))

    def test_over_short_position(self):
        result = market_making.simple_position_responsive_sizing(
            Money('2', 'BTC'),
            Money('-3', 'BTC'),
        )

        result[0].should.equal(Money('2', 'BTC'))
        result[1].should.equal(Money('0', 'BTC'))

    def test_over_long_position(self):
        result = market_making.simple_position_responsive_sizing(
            Money('2', 'BTC'),
            Money('3', 'BTC'),
        )

        result[0].should.equal(Money('0', 'BTC'))
        result[1].should.equal(Money('2', 'BTC'))

    def test_over_short_position_non_btc(self):
        result = market_making.simple_position_responsive_sizing(
            Money('2', 'ETH'),
            Money('-3', 'ETH'),
        )

        result[0].should.equal(Money('2', 'ETH'))
        result[1].should.equal(Money('0', 'ETH'))

    def test_over_short_position_fiat(self):
        result = market_making.simple_position_responsive_sizing(
            Money('2', 'USD'),
            Money('-3', 'USD'),
        )

        result[0].should.equal(Money('2', 'USD'))
        result[1].should.equal(Money('0', 'USD'))

