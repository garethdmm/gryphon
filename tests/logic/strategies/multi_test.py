"""
Some simple tests for the Multiexchange Linear Market Making strategy.
"""

import pyximport; pyximport.install()

import unittest

from gryphon.execution.strategies.builtin.multiexchange_linear import Multiexchange_linear
from gryphon.execution.harness.harness import Harness
from gryphon.lib.money import Money


class TestBitstampExchangeCoordinator(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_calculate_base_volumes_simple(self):
        """
        With a zero position, calculate_volumes should return the base_volume property
        of the strategy.
        """
        strat = Multiexchange_linear(None, None)

        strat._position = Money('0', 'BTC')

        bid_volume, ask_volume = strat.calculate_base_volumes()

        assert bid_volume == strat.base_volume
        assert ask_volume == strat.base_volume

    def test_calculate_base_volumes_harder(self):
        """
        When max_position > base_volume, calculate_volumes should return the minimum of
        the two.
        """
        strat = Multiexchange_linear(None, None)

        strat.max_position = Money('0.1', 'BTC')
        strat.base_volume = Money('0.2', 'BTC')
        strat._position = Money('0', 'BTC')

        bid_volume, ask_volume = strat.calculate_base_volumes()

        assert bid_volume == Money('0.1', 'BTC')
        assert ask_volume == Money('0.1', 'BTC')

    def test_calculate_base_volumes_hardest(self):
        """
        When we're near our maximum short position, we should place our base_volume
        amount on the bid and the order volume that would take us to our max position on
        the ask.
        """
        strat = Multiexchange_linear(None, None)

        strat.max_position = Money('0.1', 'BTC')
        strat.base_volume = Money('0.05', 'BTC')
        strat._position = Money('-0.09', 'BTC')

        bid_volume, ask_volume = strat.calculate_base_volumes()

        assert bid_volume == Money('0.05', 'BTC')
        assert ask_volume == Money('0.01', 'BTC')
