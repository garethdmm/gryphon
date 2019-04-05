import pyximport; pyximport.install()

import unittest

from cdecimal import Decimal

from gryphon.lib.exchange.coinbase_btc_usd import CoinbaseBTCUSDExchange
from gryphon.lib.money import Money
from gryphon.tests.logic.configuration.exchange import BaseConfiguration


class CoinbaseConfigurationTest(BaseConfiguration, unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.exchange_class = CoinbaseBTCUSDExchange

        # These need to match gryphon/lib/exchange/bitstamp.py
        self.DEFAULT_MARKET_FEE = Decimal('0.0022')
        self.DEFAULT_FIAT_TOLERANCE = Money('0.0001', 'USD')
        self.DEFAULT_VOLUME_TOLERANCE = Money('0.00000001', 'BTC')

        super(CoinbaseConfigurationTest, self).__init__(*args, **kwargs)
