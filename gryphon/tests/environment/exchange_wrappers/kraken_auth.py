import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
from gryphon.tests.exceptional.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestKrakenBTCEURAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = KrakenBTCEURExchange()
