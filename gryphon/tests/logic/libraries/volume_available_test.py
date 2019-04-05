import pyximport; pyximport.install()

import unittest

from gryphon.lib.exchange.exchange_order import Order as ExchangeOrder
from gryphon.lib.metrics import volume_available
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

    def test_empty(self):
        did_throw_exception = False

        try:
            liquidity = volume_available.volume_available_at_price(
                Order.BID,
                Money('250', 'USD'),
                self.empty_book,
            )
        except Exception:
            did_throw_exception = True            

        did_throw_exception.should.equal(True)

    def test_no_overlap(self):
        liquidity = volume_available.volume_available_at_price(
            Order.ASK,
            Money('250', 'USD'),
            self.basic_book,
        )

        liquidity.should.equal(Money('0', 'BTC'))

