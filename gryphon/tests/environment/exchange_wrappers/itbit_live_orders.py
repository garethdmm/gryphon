import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

from gryphon.lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange
from gryphon.tests.exceptional.exchange_wrappers.live_orders import LiveOrdersTest


class TestItBitLiveOrders(LiveOrdersTest):
    def setUp(self):
        self.exchange = ItbitBTCUSDExchange()
