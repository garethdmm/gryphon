import pyximport; pyximport.install()

from gryphon.lib.exchange.quadriga_btc_cad import QuadrigaBTCCADExchange
from gryphon.tests.exceptional.exchange_wrappers.live_orders import LiveOrdersTest


class TestQuadrigaLiveOrders(LiveOrdersTest):
    def __init__(self):
        super(TestQuadrigaLiveOrders, self).__init__()

        # Quadriga has a 10 CAD minimum order size.
        self.order1_price_amount = '10.01'
        self.order2_price_amount = '10.02'

    def setUp(self):
        self.exchange = QuadrigaBTCCADExchange()
