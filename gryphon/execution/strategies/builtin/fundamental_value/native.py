from gryphon.lib.exchange.base import Exchange
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.money import Money
from gryphon.lib.metrics import quote as quote_lib


class OrderbookSizeException(Exception):
    pass


def calculate(orderbook, depth=Money('10', 'BTC')):
    try:
        bid_quote = quote_lib.price_quote_from_orderbook(
            orderbook,
            Consts.BID,
            depth,
        )

        bid_quote_price = bid_quote['total_price']

        ask_quote = quote_lib.price_quote_from_orderbook(
            orderbook,
            Consts.ASK,
            depth,
        )

        ask_quote_price = ask_quote['total_price']

    except:
        raise OrderbookSizeException

    fundamental_quote = (bid_quote_price + ask_quote_price) / 2
    fundamental_value = fundamental_quote / depth.amount

    return fundamental_value

