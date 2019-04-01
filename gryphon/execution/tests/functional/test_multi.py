import pyximport; pyximport.install()

import os
import mock
import sure

from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exchange_order import Order

from algos.multi import Multi

class TestLinear():

    ###              ORDER BOOK                ###
    ###       BIDS                 ASKS        ###
    ###       490                  510         ###
    ###       480                  520         ###
    ###       470                  530         ###
    ###               ... etc ...              ###

    def setUp(self):
        self.exchange = mock.Mock()
        self.exchange.name = "TestExchange"
        self.exchange.currency = "USD"

        self.db = mock.Mock()

        # Fundamental value calculations are tested in test_fundamental_value.py
        # so we can just hardcode it here
        self.fundamental_value = Money("500", "USD")

        self.orderbook = {'bids': [], 'asks': []}
        for i in range(1,20):
            bid = Order(Money("500", "USD") - (i * 10), Money("1", "BTC"), self.exchange, Order.BID, order_id=None, status=None)
            ask = Order(Money("500", "USD") + (i * 10), Money("1", "BTC"), self.exchange, Order.ASK, order_id=None, status=None)
            self.orderbook['bids'].append(bid)
            self.orderbook['asks'].append(ask)

        params = {
            'max_position': 'BTC 16',
            'volume': 'BTC 2',
            'max_fiat_balance': 'USD 200000',
            'jump': 'USD 0.01',
            'base_spread': 'USD 0',
            'ignore_volume': 'BTC 0.05',
        }

        self.algo = Multi(self.exchange, self.db, debug=True, params=params)
        self.algo._max_position = None
        self.algo._position = None
        self.algo.position = mock.Mock(return_value=Money(0, "BTC"))
        self.algo.order = mock.MagicMock()
        self.algo.update_order = mock.MagicMock()

    def test_calculate_price(self):
        bid_price, ask_price = self.algo.calculate_prices( self.fundamental_value , self.orderbook)

        bid_price.should.equal(Money("490.01", "USD"))
        ask_price.should.equal(Money("509.99", "USD"))

    def test_in_between_orders(self):
        self.algo.spread = Money("15.00", "USD")

        bid_price, ask_price = self.algo.calculate_prices( self.fundamental_value , self.orderbook)

        # we should ignore the tiny orders
        bid_price.should.equal(Money("480.01", "USD"))
        ask_price.should.equal(Money("519.99", "USD"))
        
    def test_ignore_tiny_orders(self):
        # very competitive orders in this order book
        tiny_bid = Order(Money("499", "USD"), Money("0.0001", "BTC"), self.exchange, Order.BID, order_id=None, status=None)
        tiny_ask = Order(Money("501", "USD"), Money("0.0001", "BTC"), self.exchange, Order.ASK, order_id=None, status=None)

        self.orderbook['bids'].insert(0, tiny_bid)
        self.orderbook['asks'].insert(0, tiny_ask)

        bid_price, ask_price = self.algo.calculate_prices( self.fundamental_value , self.orderbook)

        # we should ignore the tiny orders
        bid_price.should.equal(Money("490.01", "USD"))
        ask_price.should.equal(Money("509.99", "USD"))

    def test_should_not_bid_cross_the_spread(self):
        close_ask = Order(Money("490.01", "USD"), Money("1", "BTC"), self.exchange, Order.ASK, order_id=None, status=None)

        self.orderbook['asks'].insert(0, close_ask)

        bid_price, ask_price = self.algo.calculate_prices( self.fundamental_value , self.orderbook)

        # bid should not cross the spread
        # ask should be normal
        bid_price.should.equal(Money("490", "USD"))
        ask_price.should.equal(Money("509.99", "USD"))

    def test_should_not_ask_cross_the_spread(self):
        close_bid = Order(Money("509.99", "USD"), Money("1", "BTC"), self.exchange, Order.BID, order_id=None, status=None)

        self.orderbook['bids'].insert(0, close_bid)

        bid_price, ask_price = self.algo.calculate_prices( self.fundamental_value , self.orderbook)

        # bid should be normal
        # ask should not cross the spread
        bid_price.should.equal(Money("490.01", "USD"))
        ask_price.should.equal(Money("510", "USD"))

    def tearDown(self):
        pass
