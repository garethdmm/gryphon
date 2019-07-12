import pyximport; pyximport.install(language_level=3)

from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.tests.exceptional.exchange_wrappers.live_orders import LiveOrdersTest


class TestGeminiBTCUSDLiveOrders(LiveOrdersTest):
    def setUp(self):
        self.exchange = GeminiBTCUSDExchange()
