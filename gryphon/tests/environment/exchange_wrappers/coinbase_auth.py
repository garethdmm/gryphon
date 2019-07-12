import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange
from gryphon.tests.environment.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestCoinbaseBTCUSDAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = CoinbaseBTCUSDExchange()
