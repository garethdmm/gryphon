import pyximport; pyximport.install()

import os
import unittest

from cdecimal import Decimal

from gryphon.lib.metrics import orderbook_strength
from gryphon.lib.exchange.exchange_order import Order as ExchangeOrder
from gryphon.lib.models.order import Order
from gryphon.lib.money import Money


class TestLiquidityFunction(unittest.TestCase):
    def setUp(self):
        self.empty_book = {
            'bids': [],
            'asks': [],
        }

        self.exchange = None

        bid = ExchangeOrder(
            Money('249', 'USD'), 
            Money('10', 'BTC'),
            self.exchange,
            Order.BID,
        )
            
        ask = ExchangeOrder(
            Money('251', 'USD'), 
            Money('10', 'BTC'),
            self.exchange,
            Order.ASK,
        )

        self.basic_book = {
            'bids': [bid],
            'asks': [ask],
        }

        bid2 = ExchangeOrder(
            Money('239', 'USD'),
            Money('10', 'BTC'),
            self.exchange,
            Order.BID,
        )

        ask2 = ExchangeOrder(
            Money('261', 'USD'),
            Money('100', 'BTC'),
            self.exchange,
            Order.ASK,
        )

        self.bigger_book = {
            'bids': [bid, bid2],
            'asks': [ask, ask2],
        }

    def test_strength_basic(self):
        bid_strength = orderbook_strength.orderbook_strength_at_slippage(
            self.basic_book,
            Order.BID,
            Money('2', 'USD'),
        )

        ask_strength = orderbook_strength.orderbook_strength_at_slippage(
            self.basic_book,
            Order.ASK,
            Money('2', 'USD'),
        )

        bid_strength.should.equal(Decimal('10'))
        ask_strength.should.equal(Decimal('10'))

    def test_strength_normal(self):
        """
        This orderbook is:
            [261, 100]
            [251, 10]
            .
            [249, 10]
            [239, 10]
        """
        bid_strength = orderbook_strength.orderbook_strength_at_slippage(
            self.bigger_book,
            Order.BID,
            Money('20', 'USD'),
        )

        ask_strength = orderbook_strength.orderbook_strength_at_slippage(
            self.bigger_book,
            Order.ASK,
            Money('20', 'USD'),
        )

        bid_strength.should.equal(Decimal('20'))
        ask_strength.should.equal(Decimal('110'))

