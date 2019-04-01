"""
Several functions around getting the "strength" of an orderbook at a certain depth.

TODO: This library needs to be generalized to multiple currencies.
"""

from gryphon.lib.money import Money
import gryphon.lib.metrics.midpoint as midpoint_lib
import gryphon.lib.metrics.volume_available as available_volume
from gryphon.lib.exchange.consts import Consts


def orderbook_strength_at_slippage(orderbook, order_type, slippage):
    """
    Get the amount of liquidity (bitoin denominated) available within [slippage]
    dollars of the top [order_type].

    Returns a decimal.
    """

    vol = Money('0', 'BTC')

    if order_type == Consts.BID:
        top_bid = orderbook['bids'][0]
        price = top_bid.price - slippage

        vol = available_volume.volume_available_at_price(Consts.ASK, price, orderbook)
    else:
        top_ask = orderbook['asks'][0]
        price = top_ask.price + slippage

        vol = available_volume.volume_available_at_price(Consts.BID, price, orderbook)

    return vol.amount


def orderbook_strength_at_slippages(orderbook, order_type, slippages):
    """
    Get the amount of liquidity (bitcoin denominated) available within [slippage]
    dollars of the top [order_type].

    Slippages should be money objects created by str'ing a float.
    Returns a decimal: decimal dict.
    """

    slippage_lookup = {}

    if order_type == Consts.BID:
        top_bid = orderbook['bids'][0]
        prices = [top_bid.price - slippage for slippage in slippages]

        slippage_lookup = {
            (top_bid.price - slippage).amount: slippage for slippage in slippages
        }

        levels = available_volume.volume_available_at_prices(
            Consts.ASK,
            prices,
            orderbook,
        )
    else:
        top_ask = orderbook['asks'][0]
        prices = [top_ask.price + slippage for slippage in slippages]

        slippage_lookup = {
            (top_ask.price + slippage).amount: slippage for slippage in slippages
        }

        levels = available_volume.volume_available_at_prices(
            Consts.BID,
            prices,
            orderbook,
        )

    levels = {
        slippage_lookup[price].amount: value.amount
        for price, value in levels.items()
    }

    return levels


def orderbook_strength_at_slippage_in_usd(orderbook, order_type, slippage):
    """
    Get the amount of liquidity (bitcoin denominated) available within [slippage]
    dollars of the top [order_type].

    Returns a decimal.
    """
    midpoint = midpoint_lib.get_midpoint_from_orderbook(orderbook, Money('20', 'BTC'))

    vol = Money('0', 'BTC')

    if order_type == Consts.BID:
        top_bid = orderbook['bids'][0]
        price = top_bid.price - slippage

        vol = available_volume.volume_available_at_price(Consts.ASK, price, orderbook)
    else:
        top_ask = orderbook['asks'][0]
        price = top_ask.price + slippage

        vol = available_volume.volume_available_at_price(Consts.BID, price, orderbook)

    return vol.amount * midpoint.amount


def orderbook_strength_at_slippages_in_usd(orderbook, order_type, slippages):
    """
    Same as orderbook_strength_at_slippage but instead of returning the levels as a
    bitcoin-denominated quantity, we return the levels as to the usd value of the
    bitcoins at that level, which we definine as level * 20btc midpoint.

    Returns a decimal: decimal dict.
    """

    midpoint = midpoint_lib.get_midpoint_from_orderbook(orderbook, Money('20', 'BTC'))

    slippage_lookup = {}

    if order_type == Consts.BID:
        top_bid = orderbook['bids'][0]
        prices = [top_bid.price - slippage for slippage in slippages]

        slippage_lookup = {
            (top_bid.price - slippage).amount: slippage for slippage in slippages
        }

        levels = available_volume.volume_available_at_prices(
            Consts.ASK,
            prices,
            orderbook,
        )
    else:
        top_ask = orderbook['asks'][0]
        prices = [top_ask.price + slippage for slippage in slippages]

        slippage_lookup = {
            (top_ask.price + slippage).amount: slippage for slippage in slippages
        }

        levels = available_volume.volume_available_at_prices(
            Consts.BID,
            prices,
            orderbook,
        )

    levels = {
        slippage_lookup[price].amount: value.amount * midpoint.amount
        for price, value in levels.items()
    }

    return levels

