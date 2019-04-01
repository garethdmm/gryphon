import termcolor as tc

from gryphon.execution.lib.exchange_color import exchange_color, legend
from gryphon.lib.exchange.exchange_factory import *
from gryphon.lib.exchange.exchange_order import Order as ExchangeOrder
from gryphon.lib.exchange.exceptions import ExchangeAPIErrorException, ExchangeAPIFailureException
from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


def start_order_book_requests(exchanges):
    order_book_requests = []

    for exchange in exchanges:
        order_book_requests.append(exchange.get_orderbook_req())

    return order_book_requests


def start_open_order_requests(exchanges):
    open_order_requests = []

    for exchange in exchanges:
        open_order_requests.append(exchange.get_open_orders_req())

    return open_order_requests


def format_order(order):
    if order:
        chunk = u"{0:15} | {1:15} | {2:15}".format(order.price, order.volume, order.price * order.volume.amount)
        chunk = exchange_color(chunk, order.exchange.name)
        if order.status == ExchangeOrder.FLAGGED:
            chunk = tc.colored(chunk, None, attrs=['reverse'])
        return chunk
    else:
        return u"{0:51}".format("")


def format_order_book(bids, asks):
    output = u""

    output += u"{0:51}     {1:51}\n".format("           Bids", "           Asks")
    output += u"{0:15} | {1:15} | {2:15} ||| {0:15} | {1:15} | {2:15}\n".format("Price", "Amount", "Value")

    # make copies so we're not popping from the original lists
    bids = list(bids)
    asks = list(asks)
    while bids or asks:
        bid = ask = None
        if bids:
            bid = bids.pop(0)
        output += format_order(bid)
        output += u" ||| "

        if asks:
            ask = asks.pop(0)
        output += format_order(ask)
        output += u"\n"

    return output


def order_book(exchange_name, include_our_orders=False, include_fees=False):
    if exchange_name:
        exchange = make_exchange_from_key(exchange_name)
        exchanges = [exchange]
    else:
        exchanges = all_exchanges()

    obr = start_order_book_requests(exchanges)
    if include_our_orders:
        oor = start_open_order_requests(exchanges)
    
    asks = []
    bids = []
    for exchange in exchanges:
        ob_req = obr.pop(0)
        if include_our_orders:
            oo_req = oor.pop(0)
        try:
            order_book = exchange.get_orderbook_resp(ob_req)
            if include_our_orders:
                open_orders = exchange.open_orders_resp(oo_req)
                order_book = exchange.remove_orders_from_orderbook(order_book, open_orders, only_flag=True)

            asks += order_book['asks'][:20]
            bids += order_book['bids'][:20]
        except (ExchangeAPIErrorException, ExchangeAPIFailureException) as e:
            logger.error("Orderbook fetch failed for %s" % exchange.friendly_name)
    asks.sort(key = lambda x: x.price.to("USD"))
    bids.sort(key = lambda x: x.price.to("USD"), reverse=True)
    
    if include_fees:
        for order in asks + bids:
            order.apply_fee()
    
    print
    # if we are showing a consolidated orderbook
    if not exchange_name:
        print(legend() + "\n")
        for ask in asks:
            ask.price = ask.price.to("USD")
        for bid in bids:
            bid.price = bid.price.to("USD")

    print(format_order_book(bids, asks))
