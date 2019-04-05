import pyximport; pyximport.install()

from gryphon.lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange
from gryphon.tests.exceptional.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestItbitBTCUSDAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = ItbitBTCUSDExchange()
