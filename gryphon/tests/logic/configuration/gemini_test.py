import pyximport; pyximport.install()

import unittest

from cdecimal import Decimal

from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.lib.money import Money
from gryphon.tests.logic.configuration.exchange import BaseConfiguration


class GeminiConfigurationTest(BaseConfiguration, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.exchange_class = GeminiBTCUSDExchange

        self.DEFAULT_MARKET_FEE = Decimal('0.0025')
        self.DEFAULT_FIAT_TOLERANCE = Money('0.0001', 'USD')
        self.DEFAULT_VOLUME_TOLERANCE = Money('0.00000001', 'BTC')

        super(GeminiConfigurationTest, self).__init__(*args, **kwargs)
