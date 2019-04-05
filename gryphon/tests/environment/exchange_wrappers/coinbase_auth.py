import pyximport; pyximport.install()

from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange
from gryphon.tests.environment.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestCoinbaseBTCUSDAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = CoinbaseBTCUSDExchange()
