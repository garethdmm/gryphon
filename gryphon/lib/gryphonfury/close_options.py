"""
This library helps determine the best option to close an open position between different
exchanges and order types.
"""

from gryphon.lib.exchange import exchange_factory
from gryphon.lib.exchange.base import Exchange
from gryphon.lib.gryphonfury import fees as fees_lib
from gryphon.lib.gryphonfury import positions
from gryphon.lib.gryphonfury import revenue as revenue_lib
from gryphon.lib.metrics import quote as quote_lib
from gryphon.lib.models.emeraldhavoc.orderbook import Orderbook
from gryphon.lib.models.order import Order
from gryphon.lib.money import Money


def get_pl_from_market_order(position_trades, orderbook, exchange_name):
    """
    Given our current position and an exchange orderbook, what would our realized p&l
    be if we closed that position right now with a market order?
    """
    pl = Money('0', 'USD')

    open_position = positions.position_delta(position_trades)
    unmatched_fees = revenue_lib.all_fees(position_trades)[0].to('USD')

    fiat_position = open_position['fiat'].to('USD')
    btc_position = open_position['BTC']

    value_of_btc = Money(0, 'BTC')

    if btc_position > 0:
        value_of_btc = quote_lib.price_quote_from_orderbook(
            orderbook,
            Order.ASK,
            btc_position,
        )['total_price']
    else:
        value_of_btc = quote_lib.price_quote_from_orderbook(
            orderbook,
            Order.BID,
            btc_position,
        )['total_price']

    revenue = fiat_position + unmatched_fees + value_of_btc.to('USD')

    exchange = exchange_factory.make_exchange_from_key(exchange_name)
    new_fee = exchange.market_order_fee * abs(value_of_btc.to('USD'))

    fees = unmatched_fees + new_fee

    return revenue, fees


def get_pl_from_open_orders(position_trades, exchange_name, open_orders):
    """
    Given our current position, and the open orders on an exchange, what would our
    realized p&l be if a market order came in and consumed our order entirely?

    Details: we naively assume that our order is sized such that it would completely
    close our position. If there is no open order on that exchange, we return None.
    """

    bids = open_orders['bids']
    asks = open_orders['asks']

    pl = Money('0', 'USD')

    open_position = positions.position_delta(position_trades)
    unmatched_fees = revenue_lib.all_fees(position_trades)[0].to('USD')

    fiat_position = open_position['fiat'].to('USD')
    btc_position = open_position['BTC']

    value_of_btc = Money(0, 'USD')

    if btc_position > 0 and len(asks) > 0:
        close_order = asks[0]  # Naively assume the first order is what we care about.

        close_price = Money(close_order[0], 'USD')

        value_of_btc = close_price * btc_position.amount
    elif btc_position <= 0 and len(bids) > 0:
        close_order = bids[0]

        close_price = Money(close_order[0], 'USD')

        value_of_btc = close_price * btc_position.amount
    else:
        return Money(0, 'USD'), Money(0, 'USD')

    revenue = fiat_position + unmatched_fees + value_of_btc.to('USD')

    exchange = exchange_factory.make_exchange_from_key(exchange_name)
    new_fee = exchange.limit_order_fee * abs(value_of_btc.to('USD'))

    fees = unmatched_fees + new_fee

    return revenue, fees


def get_pl_from_limit_order(position_trades, orderbook, exchange_name):
    """
    Given our current position and an exchange orderbook, what would our realized p&l
    be on that position if we were the top order on this exchange, in the amount and
    side that would exactly close our position, and a market order came through and took
    the whole order?
    """
    pl = Money('0', 'USD')

    open_position = positions.position_delta(position_trades)
    unmatched_fees = revenue_lib.all_fees(position_trades)[0].to('USD')

    fiat_position = open_position['fiat'].to('USD')
    btc_position = open_position['BTC']

    value_of_btc = Money(0, 'USD')

    if btc_position > 0:
        # Then we're in a long position, we want to sell, so place an order in front
        # of the top ask.
        top_ask = orderbook['asks'][0]

        close_price = top_ask.price - Money('0.01', top_ask.price.currency)

        value_of_btc = close_price * btc_position.amount
    else:
        # Then we're in a long position, we want to sell, so place an order in front
        # of the top bid.
        top_bid = orderbook['bids'][0]

        close_price = top_bid.price + Money('0.01', top_bid.price.currency)

        value_of_btc = close_price * btc_position.amount

    revenue = fiat_position + unmatched_fees + value_of_btc.to('USD')

    exchange = exchange_factory.make_exchange_from_key(exchange_name)
    new_fee = exchange.market_order_fee * abs(value_of_btc.to('USD'))

    fees = unmatched_fees + new_fee

    return revenue, fees

