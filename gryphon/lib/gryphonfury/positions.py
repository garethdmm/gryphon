"""
A small library that helps us calculate various positions. Of a trades list, of an
algorithm, of an exchange ledger. Lots of definitions of position around here.
"""

from sqlalchemy import func

from gryphon.lib.exchange.consts import Consts
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.money import Money

logger = get_logger(__name__)


def fast_position(db, start_time=None, end_time=None, exchange_name=None, volume_currency='BTC', actor='Multi'):
    """
    Get the position of an exchange or strategy quickly using sql summing instead of
    loading every trade and doing it in python.

    TODO: We should extend this to not require an actor or volume currency.
    """
    query = db.query(func.sum(Trade._volume)).join(Order).filter(Order.actor == actor)

    if start_time:
        query = query.filter(Trade.time_created >= start_time)

    if end_time:
        query = query.filter(Trade.time_created < end_time)

    if exchange_name:
        query = query.filter(Order._exchange_name == exchange_name)

    raw_bid_volume = query.filter(Trade.trade_type == Consts.BID).scalar()
    raw_ask_volume = query.filter(Trade.trade_type == Consts.ASK).scalar()

    bid_volume = Money('0', volume_currency)

    if raw_bid_volume:
        bid_volume = Money(raw_bid_volume, volume_currency)

    ask_volume = Money('0', volume_currency)

    if raw_ask_volume:
        ask_volume = Money(raw_ask_volume, volume_currency)

    position = bid_volume - ask_volume

    return position


def cached_multi_position(db):
    """
    Get the multi strategy's position quickly by summing the cached multi position of
    all ExchangeData objects.
    """
    cached_position_sum = db\
        .query(func.sum(ExchangeData._multi_position_cache))\
        .filter(ExchangeData._multi_position_cache != None)\
        .scalar()

    cached_position = Money(cached_position_sum, 'BTC')

    # This is a hack to hardcode this, but it's a last line of defense against bad
    # position data. 250 is arbitrarily chosen as a higher bound for a strange-but-not-
    # buggy position. Our max position to date was 207BTC on the crazy okcoin 3-minute
    # tick day.
    max_sane_position = Money('250', 'BTC')

    if abs(cached_position) > max_sane_position:
        raise Exception('Insane position detected: %s' % cached_position)

    return cached_position


def position_delta(trades, price_currency=None, volume_currency='BTC'):
    """
    This function calculates our position across a list of trades for both the price
    and volume currencies. This is equivalent to calculating the total amount our
    balance in the two currencies have changed, and to the difference between the
    summation of ask and bid prices for the volume currency in that list.
    
    This function, though fairly simple, can be used in coordination with other
    functions to calculate realized or unrealized profit sets of trades. See:
    realized_pl and open_pl for examples.
    """

    if not price_currency:
        price_currency = price_currency_for_trades(trades)

    fiat_position = Money('0', price_currency)
    vol_position = Money('0', volume_currency)

    for trade in trades:
        if trade.trade_type == Consts.ASK:
            vol_position -= trade.volume
            fiat_position += trade.price_in_currency(price_currency)
        else:
            vol_position += trade.volume
            fiat_position -= trade.price_in_currency(price_currency)

        fiat_position -= trade.fee_in_currency(price_currency)

    return {volume_currency: vol_position, 'fiat': fiat_position}


def btc_position_delta(trades):
    """
    Get just the bitcoin position delta for a list of trades.
    """

    btc_position = Money('0', 'BTC')

    for trade in trades:
        if trade.trade_type == Consts.ASK:
            btc_position -= trade.volume
        else:
            btc_position += trade.volume

    return btc_position


def price_currency_for_trades(trades):
    """
    Simply takes a list of trades and extracts their currency.
    """

    if not trades:
        return "USD"

    currency = trades[0].price.currency

    # If our trades are in different currencies, convert them all to USD.
    if not all([(t.price.currency == currency) for t in trades]):
        currency = "USD"

    return currency
