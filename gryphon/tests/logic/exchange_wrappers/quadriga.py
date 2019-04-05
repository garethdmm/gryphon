import pyximport; pyximport.install()

from gryphon.lib.exchange.quadriga_btc_cad import QuadrigaBTCCADExchange
from gryphon.tests.logic.exchange_wrappers.public_methods import ExchangePublicMethodsTests


class TestQuadrigaBTCCADPublicMethods(ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = QuadrigaBTCCADExchange()

