import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import os
import unittest
import sure
import mock
from decimal import Decimal

from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.models.trade import Trade

import logging
logger = logging.getLogger(__name__)

class TestTrade(unittest.TestCase):
    def setUp(self):
        self.order = mock.MagicMock()

        self.price = Money(100, "USD")
        self.fee = Money(1, "USD")
        self.volume = Money(1, "BTC")
        self.bid_trade = Trade(Consts.BID, self.price, self.fee, self.volume, "1", self.order)
        self.ask_trade = Trade(Consts.ASK, self.price, self.fee, self.volume, "2", self.order)

    def tearDown(self):
        pass

    def test_bid_position(self):
        self.bid_trade.position.should.have.key('USD')
        self.bid_trade.position.should.have.key('BTC')
        self.bid_trade.position['USD'].should.equal(Money(-101, "USD"))
        self.bid_trade.position['BTC'].should.equal(Money(1, "BTC"))

    def test_ask_position(self):
        self.ask_trade.position.should.have.key('USD')
        self.ask_trade.position.should.have.key('BTC')
        self.ask_trade.position['USD'].should.equal(Money(99, "USD"))
        self.ask_trade.position['BTC'].should.equal(Money(-1, "BTC"))

    def test_price_in_currency(self):
        self.bid_trade.price_in_currency("USD").should.equal(Money("100", "USD"))

    def test_cad_price_in_currency(self):
        self.bid_trade.price = Money(100, "CAD")
        self.bid_trade.order.exchange_rate = Decimal("0.8")

        self.bid_trade.price_in_currency("CAD").should.equal(Money("100", "CAD"))
        self.bid_trade.price_in_currency("USD").should.equal(Money("80", "USD"))

    def test_fee_in_currency(self):
        self.bid_trade.fee_in_currency("USD").should.equal(Money("1", "USD"))

    def test_cad_fee_in_currency(self):
        self.bid_trade.fee = Money(1, "CAD")
        self.bid_trade.order.exchange_rate = Decimal("0.8")

        self.bid_trade.fee_in_currency("CAD").should.equal(Money("1", "CAD"))
        self.bid_trade.fee_in_currency("USD").should.equal(Money("0.80", "USD"))

    def test_btc_fee_in_currency(self):
        self.bid_trade.fee = Money("0.01", "BTC")
        self.bid_trade.order.fundamental_value = Money(250, "CAD")
        self.bid_trade.order.exchange_rate = Decimal("0.8")

        self.bid_trade.fee_in_currency("CAD").should.equal(Money("2.5", "CAD"))
        self.bid_trade.fee_in_currency("USD").should.equal(Money("2", "USD"))
