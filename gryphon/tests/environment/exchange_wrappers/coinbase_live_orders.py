import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange
from gryphon.tests.environment.exchange_wrappers.live_orders import LiveOrdersTest


class TestCoinbaseBTCUSDLiveOrders(LiveOrdersTest):
    def setUp(self):
        self.exchange = CoinbaseBTCUSDExchange()
