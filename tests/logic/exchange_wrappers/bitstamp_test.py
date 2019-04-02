import pyximport; pyximport.install()

from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestBitstampPublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = BitstampBTCUSDExchange()

