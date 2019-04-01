"""
A very simple strategy that looks for arbitrage between Gemini and Coinbase's BTCUSD
orderbooks, and executes trades to take advantage of opportunities.

This strategy is meant to be an example, and is not fleshed-out enough to be a long-term
viable strategy.
"""

from gryphon.execution.strategies.base import Strategy
from gryphon.lib import arbitrage as arb
from gryphon.lib.exchange.consts import Consts


class SimpleArb(Strategy):
    def tick(self, open_orders):
        cross = arb.detect_directional_cross(
            self.harness.gemini_btc_usd.get_orderbook(),
            self.harness.coinbase_btc_usd.get_orderbook(),
        )

        executable_volume = arb.get_executable_volume(
            cross,
            self.harness.coinbase_btc_usd.get_balance(),
            self.harness.gemini_btc_usd.get_balance(),
        )

        if cross and executable_volume:
            self.harness.gemini_btc_usd.market_order(executable_volume, Consts.BID)
            self.harness.coinbase_btc_usd.market_order(executable_volume, Consts.ASK)

