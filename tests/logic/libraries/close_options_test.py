"""
Unit tests for gryphon.lib.gryphonfury.close_options
"""

import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import mock
import sure
import unittest

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_order import Order as ExchangeOrder
from gryphon.lib.gryphonfury import close_options
from gryphon.lib.models.exchange import Exchange
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money


class TestCloseOptions():
    def mockExchange(self):
        exchange = Exchange('TEST')
        exchange.currency = 'USD'
        exchange.market_order_fee = 0.01
        exchange.limit_order_fee = 0.01

        return exchange

    def setUp(self):
        """
        All tests start with a 1 BTC position opened with a single bid.
        """

        self.order = mock.MagicMock()

        self.price = Money('100', 'USD')
        self.fee = Money('0.05', 'USD')
        self.volume = Money('1', 'BTC')

        self.position_trades = [
            Trade(Consts.BID, self.price, self.fee, self.volume, '1', self.order),
        ]

        self.exchange_name = 'BITSTAMP_BTC_USD'

        e = self.mockExchange()

        self.open_orders = {
            'asks': [
                ['101', self.volume, Consts.ASK],
            ],
            'bids': [
                ['99', self.volume, Consts.BID],
            ],
        }

        bids = [
            ExchangeOrder(Money('99', 'USD'), Money('1', 'BTC'), e, Consts.BID),
            ExchangeOrder(Money('98', 'USD'), Money('1', 'BTC'), e, Consts.BID),
        ]

        asks = [
            ExchangeOrder(Money('101', 'USD'), Money('1', 'BTC'), e, Consts.ASK),
            ExchangeOrder(Money('102', 'USD'), Money('1', 'BTC'), e, Consts.ASK),
        ]

        self.orderbook = {'bids': bids, 'asks': asks}

    def tearDown(self):
        pass

    def test_market_order(self):
        revenue, fee = close_options.get_pl_from_market_order(
            self.position_trades,
            self.orderbook,
            self.exchange_name,
        )

        revenue.should.equal(Money('-1', 'USD'))
        fee.should.equal(Money('0.0995', 'USD'))

    def test_limit_order(self):
        revenue, fee = close_options.get_pl_from_limit_order(
            self.position_trades,
            self.orderbook,
            self.exchange_name,
        )

        # These numbers aren't even because the library tests the scenario where we beat
        # the top order by 1 cent.
        revenue.should.equal(Money('0.99', 'USD'))
        fee.should.equal(Money('0.100495', 'USD'))

    def test_open_order(self):
        revenue, fee = close_options.get_pl_from_open_orders(
            self.position_trades,
            self.exchange_name,
            self.open_orders,
        )

        revenue.should.equal(Money('1', 'USD'))
        fee.should.equal(Money('0.1005', 'USD'))
