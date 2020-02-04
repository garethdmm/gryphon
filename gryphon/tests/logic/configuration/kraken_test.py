import pyximport; pyximport.install()

import unittest

from cdecimal import Decimal

from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
from gryphon.lib.money import Money
from gryphon.tests.logic.configuration.exchange import BaseConfiguration


class KrakenConfigurationTest(BaseConfiguration, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.exchange_class = KrakenBTCEURExchange

        # These need to match gryphon/lib/exchange/bitstamp.py
        self.DEFAULT_MARKET_FEE = Decimal('0.0026')
        self.DEFAULT_FIAT_TOLERANCE = Money('0.0001', 'EUR')
        self.DEFAULT_VOLUME_TOLERANCE = Money('0.00000001', 'BTC')

        super(KrakenConfigurationTest, self).__init__(*args, **kwargs)
