import pyximport; pyximport.install(language_level=3)

from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.tests.exceptional.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestBitstampBTCUSDAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = BitstampBTCUSDExchange()
