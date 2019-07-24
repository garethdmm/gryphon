import pyximport; pyximport.install()

from gryphon.lib.exchange.binance_je import BinanceJeBTCGBPExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestBinanceJePublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = BinanceJeBTCGBPExchange()

