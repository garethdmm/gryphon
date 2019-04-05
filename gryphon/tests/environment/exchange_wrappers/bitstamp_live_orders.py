import pyximport; pyximport.install()

from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.tests.exceptional.exchange_wrappers.live_orders import LiveOrdersTest


class TestBitstampBTCUSDLiveOrders(LiveOrdersTest):
    def __init__(self):
        # BitstampBTCUSD has a $5 minimum order size.
        self.order1_price_amount = '5'
        self.order2_price_amount = '6'
        self.sleep_time = 1

    def setUp(self):
        self.exchange = BitstampBTCUSDExchange()
