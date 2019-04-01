"""
Simple functions to find the "midpoint" of an orderbook given various definitions.
"""

import gryphon.lib.metrics.quote as quote_lib
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money

DEFAULT_QUOTE_DEPTH = '10'


class OrderbookSizeException(Exception):
    pass


def get_midpoint_from_orderbook(orderbook, depth=None):
    """
    A simple function to find the midpoint at a given depth specified in the orderbook's
    volume currency.

    Returns a USD Money.
    """

    try:
        if depth is None:
            vol_currency = orderbook['asks'][0].volume.currency

            depth = Money(DEFAULT_QUOTE_DEPTH, vol_currency)

        bid_quote = quote_lib.price_quote_from_orderbook(
            orderbook,
            Consts.BID,
            depth,
        )['total_price'] / depth.amount

        ask_quote = quote_lib.price_quote_from_orderbook(
            orderbook,
            Consts.ASK,
            depth,
        )['total_price'] / depth.amount
    except:
        raise OrderbookSizeException

    return (bid_quote + ask_quote) / 2
