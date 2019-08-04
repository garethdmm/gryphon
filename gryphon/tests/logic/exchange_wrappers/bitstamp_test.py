import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.tests.logic.exchange_wrappers import public_methods


class TestBitstampPublicMethods(public_methods.ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = BitstampBTCUSDExchange()

