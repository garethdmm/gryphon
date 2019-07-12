import pyximport; pyximport.install(language_level=3)

from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestCoinbaseBTCUSDPublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = CoinbaseBTCUSDExchange()

