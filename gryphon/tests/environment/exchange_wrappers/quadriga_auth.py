import pyximport; pyximport.install(language_level=3)

from gryphon.lib.exchange.quadriga_btc_cad import QuadrigaBTCCADExchange
from gryphon.tests.exceptional.exchange_wrappers.auth_methods import ExchangeAuthMethodsTests


class TestQuadrigaBTCCADAuthMethods(ExchangeAuthMethodsTests):
    def setUp(self):
        self.exchange = QuadrigaBTCCADExchange()
