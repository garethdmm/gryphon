import pyximport; pyximport.install()

import unittest

from cdecimal import Decimal

from gryphon.lib.exchange.gemini_eth_btc import GeminiETHBTCExchange
from gryphon.lib.money import Money
from gryphon.tests.logic.configuration.exchange import BaseConfiguration


class GeminiETHBTCConfigurationTest(BaseConfiguration, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.exchange_class = GeminiETHBTCExchange

        # These need to match gryphon/lib/exchange/bitstamp.py
        self.DEFAULT_MARKET_FEE = Decimal('0.0025')
        self.DEFAULT_FIAT_TOLERANCE = Money('0.0001', 'BTC')
        self.DEFAULT_VOLUME_TOLERANCE = Money('0.00000001', 'ETH')

        super(GeminiETHBTCConfigurationTest, self).__init__(*args, **kwargs)
