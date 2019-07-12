import pyximport; pyximport.install(language_level=3)

from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestBitstampPublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = BitstampBTCUSDExchange()

