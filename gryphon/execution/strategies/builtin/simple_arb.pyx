"""
A simple strategy that looks for arbitrage between two exchange pairs' orderbooks. The
same tick logic as SuperSimpleArb, but with configurable buy and sell exchanges.

This strategy is meant to be an example, and is not fleshed-out enough to be a long-term
viable strategy. If you do use it, make sure that the exchange fees are configured
properly for both exchanges, or you will end up making seemingly-profitable trades, but
net losing money to fees.

Currently this strategy defaults to using gemini btc-usd and coinbase btc-usd as it's
buy and sell exchanges respectively unless this is overridden by other configuration.
"""

from gryphon.execution.strategies.base import Strategy
from gryphon.lib import arbitrage as arb
from gryphon.lib.exchange.consts import Consts


class SimpleArb(Strategy):
    def __init__(self, db, harness, strategy_configuration):
        super(SimpleArb, self).__init__(db, harness)

        # Configurable properties with defaults.
        self.buy_exchange = 'gemini_btc_usd'
        self.sell_exchange = 'coinbase_btc_usd'

        self.configure(strategy_configuration)

    def configure(self, strategy_configuration):
        super(SimpleArb, self).configure(strategy_configuration)

        self.init_configurable('buy_exchange', strategy_configuration)
        self.init_configurable('sell_exchange', strategy_configuration)

        self.buy_ex = self.harness.exchange_from_key(self.buy_exchange)
        self.sell_ex = self.harness.exchange_from_key(self.sell_exchange)

        self.target_exchanges = [self.buy_ex, self.sell_ex]

    def tick(self, open_orders):
        cross = arb.detect_directional_cross(
            self.buy_ex.get_orderbook(),
            self.sell_ex.get_orderbook(),
        )

        executable_volume = arb.get_executable_volume(
            cross,
            self.sell_ex.get_balance(),
            self.buy_ex.get_balance(),
        )

        if cross and executable_volume:
            self.buy_ex.market_order(executable_volume, Consts.BID)
            self.sell_ex.market_order(executable_volume, Consts.ASK)

