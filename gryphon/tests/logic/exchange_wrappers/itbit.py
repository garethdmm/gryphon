import pyximport; pyximport.install()

from gryphon.lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestItbitPublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = ItbitBTCUSDExchange()

