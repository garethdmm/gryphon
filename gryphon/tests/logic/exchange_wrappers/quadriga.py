import pyximport; pyximport.install(language_level=2 if bytes == str else 3)

from gryphon.lib.exchange.quadriga_btc_cad import QuadrigaBTCCADExchange
from gryphon.tests.logic.exchange_wrappers import public_methods


class TestQuadrigaBTCCADPublicMethods(public_methods.ExchangePublicMethodsTests):
    def setUp(self):
        self.exchange = QuadrigaBTCCADExchange()

