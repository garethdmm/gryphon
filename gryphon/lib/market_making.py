"""
A simple library for common tasks in market making strategies.
"""

from gryphon.lib.metrics import midpoint as midpoint_lib


def midpoint_centered_fixed_spread(orderbook, spread, quote_depth=None):
    """
    """
    midpoint = midpoint_lib.get_midpoint_from_orderbook(orderbook, depth=quote_depth)

    bid_price = midpoint - (midpoint * spread)
    ask_price = midpoint + (midpoint * spread)

    return bid_price, ask_price


def simple_position_responsive_sizing(max_position, current_position):
    """
    Simple order sizing logic for a market making strategy. Define a 'max_position' that
    our strategy is will to take, and place orders of that size on both sides of the
    orderbook, less whatever position we currently are in.

    e.g. position: -0.5 BTC, max_position: 2 BTC:
        return 2 BTC, 1.5 BTC

    e.g. position: 2 BTC, max_position, 2 BTC:
        return 0 BTC, 2 BTC
    """
    bid_volume = max_position
    ask_volume = max_position

    if current_position > 0:
        bid_volume = bid_volume - min(current_position, max_position)

    if current_position < 0:
        ask_volume = ask_volume - min((-1) * current_position, max_position)

    return bid_volume, ask_volume

