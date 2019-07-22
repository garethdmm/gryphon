
import pyximport; pyximport.install()

from gryphon.lib.exchange.binance_je import BinanceJeBTCEURExchange
from gryphon.tests.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestBinanceJeBTCEURAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = BinanceJeBTCEURExchange()
