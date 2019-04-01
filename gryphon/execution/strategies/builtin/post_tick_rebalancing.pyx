"""
This simple strategy mixin rebalances bitcoin balances between multiple exchanges at the
end of every nth tick, with n set by the 'bitcoin_rebalance_tick' config variable.
"""

from gryphon.execution.strategies.base import Strategy
from gryphon.execution.lib.crypto_balancing import bitcoin_rebalance


class PostTickRebalancing(Strategy):
    def post_tick(self, tick_count):
        if tick_count % self.config['bitcoin_rebalance_tick'] == 0:
            bitcoin_rebalance(self.db, self.exchange_data, self, self.execute)

        super(PostTickRebalancing, self).post_tick(tick_count)
