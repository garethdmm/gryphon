import pyximport; pyximport.install()

import unittest

from cdecimal import Decimal

from gryphon.lib.exchange.quadriga_btc_cad import QuadrigaBTCCADExchange
from gryphon.lib.money import Money
from gryphon.tests.logic.configuration.exchange import BaseConfiguration


class QuadrigaConfigurationTest(BaseConfiguration, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.exchange_class = QuadrigaBTCCADExchange

        self.DEFAULT_MARKET_FEE = Decimal('0.0025')
        self.DEFAULT_FIAT_TOLERANCE = Money('0.0001', 'CAD')
        self.DEFAULT_VOLUME_TOLERANCE = Money('0.00000001', 'BTC')

        super(QuadrigaConfigurationTest, self).__init__(*args, **kwargs)
