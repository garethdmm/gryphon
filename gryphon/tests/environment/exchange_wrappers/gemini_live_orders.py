import pyximport; pyximport.install()

from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.tests.exceptional.exchange_wrappers.live_orders import LiveOrdersTest


class TestGeminiBTCUSDLiveOrders(LiveOrdersTest):
    def setUp(self):
        self.exchange = GeminiBTCUSDExchange()
