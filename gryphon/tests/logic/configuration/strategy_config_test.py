"""
Just a few exercises for our configuration library.
"""
import pyximport; pyximport.install()
import unittest
import mock

from cdecimal import Decimal

from gryphon.lib.money import Money
from gryphon.execution.strategies.builtin.simple_market_making import SimpleMarketMaking


class TestSimpleStrategy(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestSimpleStrategy, self).__init__(*args, **kwargs)

        self.mock_harness = mock.Mock()
        self.mock_harness.exchange_from_key = mock.Mock()

    def test_empty_config(self):
        configuration = {
            'platform': {},
            'strategy': {},
            'exchanges': {},
        }

        strat = SimpleMarketMaking(None, self.mock_harness, configuration['strategy'])

        assert strat.spread == Decimal('0.01')
        assert strat.base_volume == Money('0.005', 'BTC')

    def test_simple(self):
        configuration = {
            'platform': {},
            'strategy': {
                'base_volume': Money('1', 'BTC'),
                'spread': Decimal('1.0'),
            },
            'exchanges': {},
        }
      
        strat = SimpleMarketMaking(None, self.mock_harness, configuration['strategy'])

        assert strat.spread == Decimal('1')
        assert strat.base_volume == Money('1', 'BTC')

