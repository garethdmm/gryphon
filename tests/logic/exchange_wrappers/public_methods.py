import pyximport; pyximport.install()

import logging
import os
import unittest
import sure
import mock

logger = logging.getLogger(__name__)


class ExchangePublicMethodsTests(object):
    def test_orderbook(self):
        book = self.exchange.get_orderbook()

        assert len(book['bids']) > 10
        assert len(book['asks']) > 10

    def test_ticker(self):
        ticker = self.exchange.get_ticker()

        assert all([key in ticker for key in ('high', 'low', 'last', 'volume')])

