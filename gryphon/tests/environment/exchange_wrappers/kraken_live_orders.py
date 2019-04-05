import pyximport; pyximport.install()

from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
from gryphon.tests.exceptional.exchange_wrappers.live_orders import LiveOrdersTest


class TestKrakenBTCEURLiveOrders(LiveOrdersTest):
    def __init__(self):
        # KrakenBTCEUR BTCEUR only allows resolution down to ten cents.
        self.order1_price_amount = '0.1'
        self.order2_price_amount = '0.2'
        self.sleep_time = 3  # KrakenBTCEUR is ridiculous about their rate limits.

    def setUp(self):
        self.exchange = KrakenBTCEURExchange()
