import pyximport; pyximport.install()

import os
import unittest
import sure
from mock import patch

from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.models.exchange import Exchange, Position
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.order import Order

import logging
logger = logging.getLogger(__name__)

class TestOrder(unittest.TestCase):
    def mockExchange(self):
        exchange = Exchange("TEST")
        exchange.currency = "USD"
        return exchange

    def setUp(self):
        self.price = Money(100, "USD")
        self.volume = Money(1, "BTC")
        exchange = self.mockExchange()
        self.order = Order("Test", Consts.BID, self.volume, self.price, exchange, None)

        price = Money(50, "USD")
        fee = Money(1, "USD")
        volume = Money("0.5", "BTC")
        t = Trade(Consts.BID, price, fee, volume, None, None)
        self.order.trades.append(t)

        price = Money(25, "USD")
        fee = Money(1, "USD")
        volume = Money("0.25", "BTC")
        t = Trade(Consts.BID, price, fee, volume, None, None)
        self.order.trades.append(t)

    def tearDown(self):
        pass

    def test_position(self):
        self.order.position.should.have.key('USD')
        self.order.position.should.have.key('BTC')
        self.order.position['USD'].should.equal(Money(-77, "USD"))
        self.order.position['BTC'].should.equal(Money("0.75", "BTC"))

    def test_position_change(self):
        old_position = Position()
        delta = self.order.position_change(old_position)
        delta['USD'].should.equal(Money(-77, "USD"))
        delta['BTC'].should.equal(Money("0.75", "BTC"))

    def test_reverse_position_change(self):
        old_position = self.order.position
        empty_data = {'btc_total': Money.loads("BTC 0"),
            'fiat_total': Money.loads("USD 0"),
            'time_created': 1431712831,
            'trades': [],
            'type': u'ASK'}

        self.order.was_partially_eaten(empty_data)
        delta = self.order.position_change(old_position)
        delta['USD'].should.equal(Money(77, "USD"))
        delta['BTC'].should.equal(Money("-0.75", "BTC"))

    def test_reversal(self):
        # delta from 0 to order position
        delta = self.order.position_change(Position())
        old_position = self.order.position
        self.order.reverse()
        # delta back from order position to 0
        reverse_delta = self.order.position_change(old_position)
        reverse_delta.should.equal(-delta)
