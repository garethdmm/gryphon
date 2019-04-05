import pyximport; pyximport.install()

from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestKrakenBTCEURPublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = KrakenBTCEURExchange()

