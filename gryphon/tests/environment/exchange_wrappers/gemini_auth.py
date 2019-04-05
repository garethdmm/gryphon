import pyximport; pyximport.install()

from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.tests.exceptional.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestGeminiBTCUSDAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = GeminiBTCUSDExchange()
