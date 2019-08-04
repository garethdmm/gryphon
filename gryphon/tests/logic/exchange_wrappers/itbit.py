import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

from gryphon.lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange
from gryphon.tests.logic.exchange_wrappers import public_methods


class TestItbitPublicMethods(public_methods.ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = ItbitBTCUSDExchange()

