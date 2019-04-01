"""
Tests for gryphon.lib.arbitrage.

TODO:
- Test fee/profit number functionality. This is a bit more than trivial because it's
  not guaranteed that our fee levels on a given exchange won't change.
"""

import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import unittest
import sure

from gryphon.lib import order_sliding
from gryphon.lib.exchange.exchange_order import Order
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange


class TestOrderSliding(unittest.TestCase):
    def setUp(self):
        self.bitstamp = BitstampBTCUSDExchange()

        bids1 = [
            Order(Money('1000', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.BID),
            Order(Money('500', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.BID),
        ]

        asks1 = [
            Order(Money('1001', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.ASK),
            Order(Money('1501', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.ASK),
        ]

        self.basic_a = {'bids': bids1, 'asks': asks1}

        bids2 = [
            Order(Money('1000', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.BID),
            Order(Money('900', 'USD'), Money('0.01', 'BTC'), self.bitstamp, Consts.BID),
            Order(Money('500', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.BID),
        ]

        asks2 = [
            Order(Money('1001', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.ASK),
            Order(Money('1100', 'USD'), Money('0.01', 'BTC'), self.bitstamp, Consts.BID),
            Order(Money('1501', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.ASK),
        ]

        self.basic_b = {'bids': bids2, 'asks': asks2}

    def tearDown(self):
        pass
  
    def test_trivial_bid(self):
        mode = Consts.BID
        initial_price = Money('999', 'USD')
        orderbook = self.basic_a
        ignore_volume = Money('0.001', 'BTC')
        jump = Money('0.01', 'USD')
        max_slide = None

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('500.01', 'USD'))

    def test_trivial_ask(self):
        mode = Consts.ASK
        initial_price = Money('1002', 'USD')
        orderbook = self.basic_a
        ignore_volume = Money('0.001', 'BTC')
        jump = Money('0.01', 'USD')
        max_slide = None

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('1500.99', 'USD'))

    def test_max_slide_bid(self):
        mode = Consts.BID
        initial_price = Money('999', 'USD')
        orderbook = self.basic_a
        ignore_volume = Money('0.001', 'BTC')
        jump = Money('0.01', 'USD')
        max_slide = Money('100', 'USD')

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('899', 'USD'))

    def test_max_slide_ask(self):
        mode = Consts.ASK
        initial_price = Money('1002', 'USD')
        orderbook = self.basic_a
        ignore_volume = Money('0.001', 'BTC')
        jump = Money('0.01', 'USD')
        max_slide = Money('100', 'USD')

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('1102', 'USD'))

    def test_jump_bid(self):
        mode = Consts.BID
        initial_price = Money('999', 'USD')
        orderbook = self.basic_a
        ignore_volume = Money('0.001', 'BTC')
        jump = Money('100', 'USD')
        max_slide = None

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('600', 'USD'))

    def test_jump_ask(self):
        mode = Consts.ASK
        initial_price = Money('1002', 'USD')
        orderbook = self.basic_a
        ignore_volume = Money('0.001', 'BTC')
        jump = Money('100', 'USD')
        max_slide = None

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('1401', 'USD'))

    def test_ignore_bid(self):
        mode = Consts.BID
        initial_price = Money('999', 'USD')
        orderbook = self.basic_b
        ignore_volume = Money('0.1', 'BTC')
        jump = Money('0.01', 'USD')
        max_slide = None

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('500.01', 'USD'))

    def test_ignore_ask(self):
        mode = Consts.ASK
        initial_price = Money('1002', 'USD')
        orderbook = self.basic_b
        ignore_volume = Money('0.1', 'BTC')
        jump = Money('0.01', 'USD')
        max_slide = None

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('1500.99', 'USD'))

    def test_do_not_ignore_bid(self):
        mode = Consts.BID
        initial_price = Money('999', 'USD')
        orderbook = self.basic_b
        ignore_volume = Money('0.001', 'BTC')
        jump = Money('0.01', 'USD')
        max_slide = None

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('900.01', 'USD'))

    def test_do_not_ignore_ask(self):
        mode = Consts.ASK
        initial_price = Money('1002', 'USD')
        orderbook = self.basic_b
        ignore_volume = Money('0.001', 'BTC')
        jump = Money('0.01', 'USD')
        max_slide = None

        new_price = order_sliding.slide_order(
            mode,
            initial_price,
            orderbook,
            ignore_volume,
            jump,
            max_slide,
        )

        new_price.should.equal(Money('1099.99', 'USD'))


class TestOrderPriceLogic(unittest.TestCase):
    def setUp(self):
        #o = Order(Money('600', 'USD'), Money('1', 'BTC'), self.bitstamp, Consts.BID),
        pass

    def tearDown(self):
        pass

    def test_widen_bid(self):
        price = Money('1', 'USD')
        change = Money('0.1', 'USD')
        mode = Consts.BID

        result = order_sliding.widen_price(mode, price, change)

        result.should.equal(Money('0.9', 'USD'))

    def test_widen_ask(self):
        price = Money('1', 'USD')
        change = Money('0.1', 'USD')
        mode = Consts.ASK

        result = order_sliding.widen_price(mode, price, change)

        result.should.equal(Money('1.1', 'USD'))

    def test_narrow_bid(self):
        price = Money('1', 'USD')
        change = Money('0.1', 'USD')
        mode = Consts.BID

        result = order_sliding.narrow_price(mode, price, change)

        result.should.equal(Money('1.1', 'USD'))

    def test_narrow_ask(self):
        price = Money('1', 'USD')
        change = Money('0.1', 'USD')
        mode = Consts.ASK

        result = order_sliding.narrow_price(mode, price, change)

        result.should.equal(Money('0.9', 'USD'))

    def test_widen_bid_b(self):
        price = Money('1e6', 'BCH')
        change = Money('100', 'BCH')
        mode = Consts.BID

        result = order_sliding.widen_price(mode, price, change)

        result.should.equal(Money('999900', 'BCH'))

    def test_widen_ask_b(self):
        price = Money('1e6', 'BCH')
        change = Money('100', 'BCH')
        mode = Consts.ASK

        result = order_sliding.widen_price(mode, price, change)

        result.should.equal(Money('1000100', 'BCH'))

    def test_narrow_bid_b(self):
        price = Money('1e6', 'BCH')
        change = Money('100', 'BCH')
        mode = Consts.BID

        result = order_sliding.narrow_price(mode, price, change)

        result.should.equal(Money('1000100', 'BCH'))

    def test_narrow_ask(self):
        price = Money('1e6', 'BCH')
        change = Money('100', 'BCH')
        mode = Consts.ASK

        result = order_sliding.narrow_price(mode, price, change)

        result.should.equal(Money('999900', 'BCH'))

    def test_deeper_price_bid(self):
        price_a = Money('1', 'USD')
        price_b = Money('0.9', 'USD')
        mode = Consts.BID

        result = order_sliding.is_deeper_price(mode, price_a, price_b)

        result.should.equal(False)

        result = order_sliding.is_deeper_price(mode, price_b, price_a)

        result.should.equal(True)

    def test_deeper_price_ask(self):
        price_a = Money('1', 'USD')
        price_b = Money('0.9', 'USD')
        mode = Consts.ASK

        result = order_sliding.is_deeper_price(mode, price_a, price_b)

        result.should.equal(True)

        result = order_sliding.is_deeper_price(mode, price_b, price_a)

        result.should.equal(False)

    def test_deeper_price_bid_b(self):
        price_a = Money('1000', 'ETH')
        price_b = Money('200', 'ETH')
        mode = Consts.BID

        result = order_sliding.is_deeper_price(mode, price_a, price_b)

        result.should.equal(False)

        result = order_sliding.is_deeper_price(mode, price_b, price_a)

        result.should.equal(True)

    def test_deeper_price_ask_b(self):
        price_a = Money('1000', 'ETH')
        price_b = Money('200', 'ETH')
        mode = Consts.ASK

        result = order_sliding.is_deeper_price(mode, price_a, price_b)

        result.should.equal(True)

        result = order_sliding.is_deeper_price(mode, price_b, price_a)

        result.should.equal(False)

