"""
An extension of the trivial_mm builtin strategy demonstrating a few more features of the
harness: logging, strategy configuration, and adding extra data to orders.
"""

from cdecimal import Decimal

from gryphon.execution.strategies.base import Strategy
from gryphon.lib import market_making as mm
from gryphon.lib.metrics import midpoint as midpoint_lib
from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts


class ImprovedMarketMaking(Strategy):
    def __init__(self, db, harness, strategy_configuration):
        super(ImprovedMarketMaking, self).__init__(db, harness)

        # Immutable properties.
        self.exchange_name = 'BITSTAMP_BTC_USD'
        self.target_exchanges = ['BITSTAMP_BTC_USD']

        # Configurable properties with defaults.
        self.spread = Decimal('0.10')
        self.base_volume = Money('0.005', 'BTC')

        self.configure(strategy_configuration)

    def configure(self, strategy_configuration):
        super(ImprovedMarketMaking, self).configure(strategy_configuration)

        self.init_configurable('spread', strategy_configuration)
        self.init_configurable('base_volume', strategy_configuration)

    def tick(self, current_orders):
        self.harness.bitstamp_btc_usd.cancel_all_open_orders()

        ob = self.harness.bitstamp_btc_usd.get_orderbook()
        midpoint = midpoint_lib.get_midpoint_from_orderbook(ob)

        bid_price = midpoint - (midpoint * self.spread)
        ask_price = midpoint + (midpoint * self.spread)

        self.mid_tick_logging(midpoint, bid_price, ask_price)

        bid_volume, ask_volume = mm.simple_position_responsive_sizing(
            self.base_volume,
            self.position,
        )

        if bid_volume > 0:
            self.harness.bitstamp_btc_usd.limit_order(
                Consts.BID,
                bid_volume,
                bid_price,
                extra_data={'fundamental_value': midpoint},
        )

        if ask_volume > 0:
            self.harness.bitstamp_btc_usd.limit_order(
                Consts.ASK,
                ask_volume,
                ask_price,
                extra_data={'fundamental_value': midpoint},
            )

    def mid_tick_logging(self, midpoint, bid_price, ask_price):
        self.harness.log('Prospective bid: '.ljust(20) + str(bid_price), color='blue')
        self.harness.log('Midpoint: '.ljust(20) + str(midpoint), color='blue')
        self.harness.log('Prospective ask: '.ljust(20) + str(ask_price), color='blue')

