import pyximport; pyximport.install()

from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
from gryphon.tests.exceptional.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestKrakenBTCEURAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = KrakenBTCEURExchange()
