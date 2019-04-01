import pyximport; pyximport.install()

from gryphon.lib.exchange.quadriga_btc_cad import QuadrigaBTCCADExchange
from tests.exceptional.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestQuadrigaBTCCADAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = QuadrigaBTCCADExchange()
