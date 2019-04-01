"""
These function calculate the volume available to buy/sell at a given price point in an
orderbook. Another phrase for this would be "orderbook levels".
"""

from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts


def volume_available_at_price(mode, price, orderbook):
    """
    This uses bid/ask to represent intention, not the side of the order book to look
    at. volume_avail_at_price(ASK, 250) will give you how many bitcoins can be sold
    for at least $250 in the orderbook.
    """
    if(mode == Consts.BID):
        orders = orderbook.get('asks', [])
    elif(mode == Consts.ASK):
        orders = orderbook.get('bids', [])
    else:
        raise ValueError('mode must be one of ask/bid')

    if not orders:
        raise Exception('no orders on one side of the book.')

    volume_available = Money('0', 'BTC')

    for order in orders:
        if mode == Consts.BID:
            if order.price <= price:
                volume_available += order.volume
            else:
                break
        elif mode == Consts.ASK:
            if order.price >= price:
                volume_available += order.volume
            else:
                break

    return volume_available


def volume_available_at_prices(mode, prices, orderbook):
    """
    Same as above but gets the volume available at multiple levels at once. This
    gives us a substantial performance bump which is necessary in the importer.

    Prices should be money object created by str'ing a float.
    Returns a decimal: Money dict. It would be more consistent with the singular
    level function to return a Money: Money, but money is unhashable.
    """

    if mode == Consts.BID:
        orders = orderbook.get('asks', [])
    elif mode == Consts.ASK:
        orders = orderbook.get('bids', [])
    else:
        raise ValueError('mode must be one of ask/bid')

    if not orders:
        raise Exception('no orders on one side of the book.')

    volume_available = Money('0', 'BTC')
    levels = {}
    i = 0
    j = 0

    # Loop until one of the two lists is exhausted.
    if mode == Consts.BID:
        prices = sorted(prices, reverse=False)

        while True:
            if orders[i].price <= prices[j]:
                volume_available += orders[i].volume
                i = i + 1
            elif orders[i].price > prices[j]:
                levels[prices[j].amount] = volume_available
                j = j + 1

            if i == len(orders) or j == len(prices):
                break

    elif mode == Consts.ASK:
        prices = sorted(prices, reverse=True)

        while True:
            if orders[i].price >= prices[j]:
                volume_available += orders[i].volume
                i = i + 1
            elif orders[i].price < prices[j]:
                levels[prices[j].amount] = volume_available
                j = j + 1

            if i == len(orders) or j == len(prices):
                break

    # If we broke because we ran out of orders, fill in the rest of the dict.
    while j < len(prices):
        levels[prices[j].amount] = volume_available
        j += 1

    return levels

