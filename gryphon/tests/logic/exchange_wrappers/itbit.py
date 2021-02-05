import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

from gryphon.lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestItbitPublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = ItbitBTCUSDExchange()

