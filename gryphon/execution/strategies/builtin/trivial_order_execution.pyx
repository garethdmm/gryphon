"""
A very simple execution strategy meant to demonstrate the implementation of an
execution strategy on the gryphon framework. This strategy does nothing except accept
an exchange name, BID/ASK, and a volume from the command line, and executes the implied
order on the given exchange through a market order.
"""

from gryphon.execution.strategies.base import Strategy


class TrivialExecutionStrategy(ExecutionStrategy):
    def tick(self):
        exchange = self.harness.exchange.from_key(self.args['exchange'])
        exchange.market_order(self.args['mode'], self.args['volume'])

