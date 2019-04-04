import pyximport; pyximport.install()

from gryphon.lib.exchange.itbit_btc_usd import ItbitBTCUSDExchange
from tests.exceptional.exchange_wrappers.live_orders import LiveOrdersTest


class TestItBitLiveOrders(LiveOrdersTest):
    def setUp(self):
        self.exchange = ItbitBTCUSDExchange()
