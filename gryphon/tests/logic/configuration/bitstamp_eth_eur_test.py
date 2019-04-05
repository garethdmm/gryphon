import pyximport; pyximport.install()

import unittest

from cdecimal import Decimal

from gryphon.lib.exchange.bitstamp_eth_eur import BitstampETHEURExchange
from gryphon.lib.money import Money
from gryphon.tests.logic.configuration.exchange import BaseConfiguration


class BitstampETHEURConfigurationTest(BaseConfiguration, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.exchange_class = BitstampETHEURExchange

        # These need to match gryphon/lib/exchange/bitstamp.py
        self.DEFAULT_MARKET_FEE = Decimal('0.0005')
        self.DEFAULT_FIAT_TOLERANCE = Money('0.0001', 'EUR')
        self.DEFAULT_VOLUME_TOLERANCE = Money('0.00000001', 'ETH')

        super(BitstampETHEURConfigurationTest, self).__init__(*args, **kwargs)
