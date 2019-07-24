import pyximport; pyximport.install()

from gryphon.lib.exchange.binance_je import BinanceJeBTCGBPExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestBinanceJePublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = BinanceJeBTCGBPExchange()


class TestBinanceJeSpecificMethods(object):
    def setup(self):
        self.exchange = BinanceJeBTCGBPExchange()

    def test_ping(self):
        response = self.exchange.ping()
        assert response == {}

