"""
This is a very simple market making strategy to demonstrate use of the Gryphon
framework. For being only 23 lines of code, this strategy has some very subtle logic to
it.

Every tick, we place orders on both sides of the orderbook at a 1% spread back from the
midpoint on the Coinbase BTCUSD pair. The orders start at a size of 2 BTC. If either of 
these orders are filled in any volume, the strategy is now at a net position. We want to
limit our absolute risk, so the strategy has a maximum position it will enter. To avoid
going past our max position, the order size on the side of our position is decreased
so that we should never be offering an order that would take us past our maximum if it
were filled.

This strategy is just an example, and should not be used for real trading.
"""

from cdecimal import Decimal

from gryphon.execution.strategies.base import Strategy
from gryphon.lib import market_making as mm
from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts


class SimpleMarketMaking(Strategy):
    def tick(self, current_orders):
        self.harness.bitstamp_btc_usd.cancel_all_open_orders()

        ob = self.harness.bitstamp_btc_usd.get_orderbook()

        bid_price, ask_price = mm.midpoint_centered_fixed_spread(ob, Decimal('0.01'))

        bid_volume, ask_volume = mm.simple_position_responsive_sizing(
            Money('2', 'BTC'),
            self.position,
        )

        if bid_volume > 0:
            self.harness.bitstamp_btc_usd.limit_order(Consts.BID, bid_volume, bid_price)

        if ask_volume > 0:
            self.harness.bitstamp_btc_usd.limit_order(Consts.ASK, ask_volume, ask_price)

