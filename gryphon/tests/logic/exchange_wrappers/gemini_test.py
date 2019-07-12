import pyximport; pyximport.install(language_level=3)

from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestGeminiBTCUSDPublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = GeminiBTCUSDExchange()

