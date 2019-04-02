"""
Just a few exercises for our configuration library.
"""
import pyximport; pyximport.install()
import unittest

from cdecimal import Decimal

from gryphon.lib.money import Money
from gryphon.execution.strategies.builtin.improved_market_making import ImprovedMarketMaking


class TestSimpleStrategy(unittest.TestCase):
    def test_empty_config(self):
        configuration = {
            'platform': {},
            'strategy': {},
            'exchanges': {},
        }
      
        strat = ImprovedMarketMaking(None, None, configuration['strategy'])

        assert strat.spread == Decimal('0.10')
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
      
        strat = ImprovedMarketMaking(None, None, configuration['strategy'])

        assert strat.spread == Decimal('1')
        assert strat.base_volume == Money('1', 'BTC')
