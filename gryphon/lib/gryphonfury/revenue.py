"""
A library of functions having to do with getting revenue/profit and their several
varieties (open, realized, as a series).
"""

from collections import defaultdict
import copy
from more_itertools import chunked
from operator import attrgetter

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from gryphon.lib.exchange.consts import Consts
import gryphon.lib.gryphonfury.fees as fees_lib
import gryphon.lib.gryphonfury.positions as positions
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.money import Money
logger = get_logger(__name__)


def fast_revenue_in_period(db, start_time, end_time):
    """
    This achieves a faster revenue calculation than revenue_in_period through math and
    better queries. Previous function is roughly O(n^2) in the number of trades in the
    period and this one is likely O(logn) for a low constant.

    Refer to the helper function 
    get_revenue_in_period_given_positions_and_position_trades to see the heavy lifting
    """

    start_position, end_position = get_start_and_end_position(db, start_time, end_time)

    start_open_position_trades, end_open_position_trades = get_start_and_end_position_trades(db, start_time, end_time, start_position, end_position)

    revenue = get_revenue_in_period_given_positions_and_position_trades(
        db,
        start_time,
        end_time,
        start_position,
        end_position,
        start_open_position_trades,
        end_open_position_trades,
    )

    return revenue


def fast_profit_in_period(db, start_time, end_time):
    """
    Get profit in a period efficiently. If you are calculating revenue and profit at
    once, use fast_revenue_fees_profit_in_period for better performance.
    """

    revenue = fast_revenue_in_period(db, start_time, end_time)
    fees = fees_lib.get_matched_trading_fees_in_period(db, start_time, end_time)

    profit = revenue - fees

    return profit


def fast_revenue_fees_profit_in_period(db, start_time, end_time):
    """
    This function gives the same results as fast_(revenue|profit)_in_period but avoids
    duplicated computation between them for better performance.
    """

    # First get the start and end positions.
    start_position, end_position = get_start_and_end_position(db, start_time, end_time)

    # Now get the list of trades that created these positions.
    start_open_position_trades, end_open_position_trades = get_start_and_end_position_trades(db, start_time, end_time, start_position, end_position)

    revenue = get_revenue_in_period_given_positions_and_position_trades(
        db,
        start_time,
        end_time,
        start_position,
        end_position,
        start_open_position_trades,
        end_open_position_trades,
    )

    matched_fees = get_matched_fees_in_period_given_position_trades(
        db,
        start_time,
        end_time,
        start_open_position_trades,
        end_open_position_trades,
    )

    profit = revenue - matched_fees

    return revenue, matched_fees, profit


def get_matched_fees_in_period_given_position_trades(db, start_time, end_time, start_open_position_trades, end_open_position_trades):
    """
    This function is used for getting matched fees in a period efficiently if we
    already have the open positions and trades for those positions.

    It takes the start/ending positions for a period and the trades for those
    positions and finds the matched fees in that period, which the fees in the period
    plus fees on the open position at the beginning of the period minus fees on
    the open position at the end of the period.
    """

    start_position_fee = sum(
        [t.fee_in_usd for t in start_open_position_trades]
    )

    end_position_fee = sum(
        [t.fee_in_usd for t in end_open_position_trades]
    )

    unmatched_fees = fees_lib.get_all_fees_in_period_in_usd(db, start_time, end_time)
    matched_fees = unmatched_fees + start_position_fee - end_position_fee

    return matched_fees


def get_revenue_in_period_given_positions_and_position_trades(db, start_time, end_time, start_position, end_position, start_open_position_trades, end_open_position_trades):
    """
    This takes the start/ending positions for a period and the trades for those
    positions and finds the realized revenue in that period.

    The math is tough to write out in ascii but the idea is:
    revenue = total_asks_price - total_bids_price

    Because we only consider realized revenue in a period, the complexity of this
    function that we have to include the trades which created the open position at the
    beginning of this period, and remove the trades which created the final position
    in this period.
    """

    # Get the total price sum for all asks and bids in this period.
    asks, bids = get_total_asks_and_bids_prices_in_period_in_usd(
        db,
        start_time,
        end_time,
    )

    # Now determine the total price of creating these positions, so we can remove
    # these totals from asks or bids.
    start_position_price = sum(
        [t.price_in_usd for t in start_open_position_trades]
    )

    end_position_price = sum(
        [t.price_in_usd for t in end_open_position_trades]
    )

    # Add the price of the starting position to asks or bids, depending on whether
    # the position was long or short. We do this because this position was closed in
    # the period we are looking at now, so it's realized revenue belongs to this
    # period.
    if start_position > 0:
        bids = bids + start_position_price
    else:
        asks = asks + start_position_price

    # Remove the price of trades that contributed to our position at the end of the
    # period. We do this because this position will be closed in the next period, so
    # doesn't represent realized revenue in this period.
    if end_position > 0:
        bids = bids - end_position_price
    else:
        asks = asks - end_position_price

    # Having accounted for starting and ending positions, the calculation is
    # simply this:
    revenue = asks - bids

    return revenue


def get_start_and_end_position(db, start_time, end_time):
    """
    Helper function to get the positions at the beginning and end of a period
    efficiently.
    """

    start_position = positions.fast_position(
        db,
        end_time=start_time,
    )

    # We calculate end_position from the beginning of the day and then add the
    # start position for performance.
    end_position = positions.fast_position(
        db,
        start_time=start_time,
        end_time=end_time,
    )

    end_position = start_position + end_position

    return start_position, end_position


def get_start_and_end_position_trades(db, start_time, end_time, start_position, end_position):
    """
    Helper function to get the position trades at the start and end of a period
    efficiently.
    """

    start_open_position_trades = open_position_trades(
        start_position,
        db,
        start_time,
    )

    end_open_position_trades = open_position_trades(
        end_position,
        db,
        end_time,
    )

    return start_open_position_trades, end_open_position_trades


def get_total_asks_and_bids_prices_in_period_in_usd(db, start_time, end_time):
    totals = db.query(
            func.sum(Trade.price_in_usd),
            Order.order_type,
        )\
        .join(Order)\
        .filter(Order.actor == "Multi")\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .group_by(Order.order_type)\
        .all()

    # Default these to zero because we can have zero trades of a type in a small
    # period.
    bids = Money(0, 'USD')
    asks = Money(0, 'USD')

    for total in totals:
        order_type = total[1]
        price_in_usd = Money(total[0], 'USD')

        if order_type == Order.BID:
            bids = price_in_usd
        elif order_type == Order.ASK:
            asks = price_in_usd

    return asks, bids


### Slower functions below this line that still have certain uses ###


def profit_data(matched_trades, price_currency=None, volume_currency='BTC'):
    """
    Take a matched_trades object and construct profit, revenue, fees, and
    volume_currency_fees summary stats from it.
    """

    if not price_currency:
        price_currency = price_currency_for_trades(matched_trades)

    position = Money('0', volume_currency)

    revenue = Money('0', price_currency)
    fees = Money('0', price_currency)
    volume_currency_fees = Money('0', volume_currency)

    for trade in matched_trades:
        if trade.trade_type == Consts.ASK:
            position -= trade.volume
            revenue += trade.price_in_currency(price_currency)
        else:
            position += trade.volume
            revenue -= trade.price_in_currency(price_currency)

        # The USD equivalent of these fees get included in fees below, but we still
        # want to track them seperately.
        if trade.fee.currency == volume_currency:
            volume_currency_fees += trade.fee

        fees += trade.fee_in_currency(price_currency)

    if position != Money('0', volume_currency):
        raise ValueError("Matched Trades must sum up to 0 %s" % volume_currency)

    profit = revenue - fees

    return profit, revenue, fees, volume_currency_fees


def all_fees(trades, price_currency=None, volume_currency='BTC'):
    """
    Return the fiat equivalent fees for a list of trades and the exact BTC amount of any
    BTC fees (their USD value is still included in the total).
    """

    if not price_currency:
        price_currency = price_currency_for_trades(trades)

    all_fees = Money('0', price_currency)
    all_volume_currency_fees = Money('0', volume_currency)

    for t in trades:
        if t.fee.currency == volume_currency:
            all_volume_currency_fees += t.fee

        all_fees += t.fee_in_currency(price_currency)

    return all_fees, all_volume_currency_fees


def realized_pl(matched_trades, price_currency=None, volume_currency='BTC'):
    """
    Take a matched_trades object and return our realized profit in the price currency
    over those trades. We do this with the insight that for a matched_trades object,
    the position_delta in the volume currency will be zero, and the position delta in
    the price currency will be our realized profit.
    """

    realized_position = positions.position_delta(
        matched_trades,
        price_currency,
        volume_currency,
    )

    if realized_position[volume_currency] != Money('0', volume_currency):
        raise ValueError('Matched Trades must sum up to 0 %s' % volume_currency)

    realized_pl = realized_position['fiat']

    return realized_pl


def open_pl(open_position_trades, fundamental_value, price_currency=None, volume_currency='BTC'):
    """
    Take in an open_position_trades object and the current fundamental value, and use
    that to calculate our current unrealized profit on that position. This is done
    simply because the fiat position on those open_position_trades is the price we
    paid to open that position, and then the unrealized profit is our current 
    expectation of the value of that position (position * fundamental_value).
    """

    open_position = positions.position_delta(
        open_position_trades,
        price_currency,
        volume_currency=volume_currency,
    )

    fiat_position = open_position['fiat']
    volume_position = open_position[volume_currency]

    value_of_volume_position = fundamental_value * volume_position.amount

    open_pl = fiat_position + value_of_volume_position

    return open_pl


def copy_trade(trade):
    """
    Make a modifiable copy of a Trade object for use in split_trades.
    """
    new_trade = Trade(
        trade.trade_type,
        copy.copy(trade.price),
        copy.copy(trade.fee),
        copy.copy(trade.volume),
        trade.exchange_trade_id,
        None,
    )

    new_trade.time_created = trade.time_created

    # This is kinda janky: add a temporary property so we don't need to bring orders
    # into the copy. This never gets saved since these SQLAlchemy objects are never
    # attached to a session.
    new_trade._exchange_rate = trade.exchange_rate
    new_trade._exchange_name = trade.exchange_name
    new_trade._fundamental_value = trade.fundamental_value

    return new_trade


def split_trades(trades, price_currency='USD', volume_currency='BTC'):
    """
    This function creates the matched_trades and position_trades objects. Matched_trades
    is a list of pairs of semi-real trades, in which the first fake-trade represents a
    chunk of a real trade that opened a position, and the second fake-trade represents
    the chunk of another real trade that closed the first position. In this way the pair
    represents a complete loop of an open-and-closing of a position. This structure is
    very useful for several purposes.
    """

    # This is slow but safer for now, don't want to modify original array.
    trades_copy = []

    for t in trades:
        # We don't need orders here, so we could probaby use SimpleTrade.
        tc = copy_trade(t)
        trades_copy.append(tc)

    trades = trades_copy
    trades.sort(key=lambda t: t.time_created)

    total_volume = sum([t.volume for t in trades])
    total_price = sum([t.price_in_currency(price_currency) for t in trades])

    bids = []
    asks = []

    for t in trades:
        if t.trade_type == Consts.BID:
            bids.append(t)
        else:
            asks.append(t)

    matched_trades = []

    while bids and asks:
        if bids[0].volume < asks[0].volume:
            active = bids.pop(0)
            trades_to_match = asks
        else:
            active = asks.pop(0)
            trades_to_match = bids

        if active.volume > 0:
            matched_trades.append(active)

        volume_to_match = active.volume

        while volume_to_match > 0:
            match = trades_to_match[0]

            if match.volume <= volume_to_match:  # We totally match.
                volume_to_match -= match.volume
                match = trades_to_match.pop(0)  # Actually remove it.

                if match.volume > 0:
                    matched_trades.append(match)
            else:  # We match part of the opposite.
                orig_price = match.price
                orig_volume = match.volume

                # Split the partial match into 2 trades.
                fraction = volume_to_match / match.volume
                matched_partial_trade = copy_trade(match)
                matched_partial_trade.price = match.price * fraction
                matched_partial_trade.fee = match.fee * fraction
                matched_partial_trade.volume = volume_to_match

                old_fraction = (match.volume - volume_to_match) / match.volume
                match.price *= old_fraction
                match.fee *= old_fraction
                match.volume -= volume_to_match

                assert abs(match.price + matched_partial_trade.price - orig_price) < 1e-10
                assert abs(match.volume + matched_partial_trade.volume - orig_volume) < 1e-10

                if matched_partial_trade.volume > 0:
                    matched_trades.append(matched_partial_trade)

                volume_to_match = 0

    assert bids == [] or asks == []  # One should be empty.

    position_trades = bids + asks

    # Assert that our matched_trades are matched.
    matched_position = positions.position_delta(
        matched_trades,
        price_currency=price_currency,
        volume_currency=volume_currency,
    )

    assert matched_position[volume_currency] == Money('0', volume_currency)

    # Assert that our total price and volume haven't changed.
    new_total_volume = sum([t.volume for t in (matched_trades + position_trades)])
    new_total_price = sum([
        t.price_in_currency(price_currency) for t in (matched_trades + position_trades)
    ])

    assert abs(new_total_volume - total_volume) < 1e-10, \
        "%s != %s" % (new_total_volume, total_volume)

    assert abs(new_total_price - total_price) < 1e-10, \
        "%s != %s" % (new_total_price, total_price)

    return matched_trades, position_trades


def profit_units(matched_trades, price_currency=None):
    """
    Takes in a matched_trades object and returns a profit_units object. Profit units are
    simply all the steps that created realized profit in that list. E.g. a period with
    a 1 btc ask at $10 and a 0.1 btc bid at $9 will have a single profit unit with a
    value of $0.10.

    Usually we only use this function when we want to display the time series of profit
    in a given period. Other functions are faster for just getting the raw numbers.
    """

    if not price_currency:
        price_currency = price_currency_for_trades(matched_trades)

    profit_units = []

    for t1, t2 in chunked(matched_trades, 2):
        assert(t1.volume == t2.volume)

        if t1.trade_type == Consts.ASK and t2.trade_type == Consts.BID:
            ask = t1
            bid = t2
        elif t1.trade_type == Consts.BID and t2.trade_type == Consts.ASK:
            bid = t1
            ask = t2
        else:
            raise ValueError("matching trades are not opposite types")

        ask_price = ask.price_in_currency(price_currency)
        bid_price = bid.price_in_currency(price_currency)
        revenue = ask_price - bid_price

        ask_fee = ask.fee_in_currency(price_currency)
        bid_fee = bid.fee_in_currency(price_currency)
        fees = ask_fee + bid_fee

        profit = revenue - fees

        unit = {
            'time': max(t1.time_created, t2.time_created),
            'profit': profit,
            'revenue': revenue,
            'exchanges': [t1.exchange_name, t2.exchange_name],
        }

        profit_units.append(unit)

    return profit_units


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


def open_position_trades(open_position_offset, db, start_time, volume_currency='BTC', strategy_actor='Multi'):
    """
    Find the last n trades from the previous day which opened the position we had
    before the day closed. We just scan backwards from the end of the day, finding
    trades of the correct type (ASK/BID) that add up to more volume than our position
    offset then we trim the last trade to the correct size so we have an exact set of
    trades.
    """

    if open_position_offset == Money('0', volume_currency):
        return []
    elif open_position_offset > Money('0', volume_currency):
        trade_type = Consts.BID
    else:
        trade_type = Consts.ASK

    open_position_trades = []

    while sum([t.volume for t in open_position_trades]) < abs(open_position_offset):
        query = db.query(Trade).join(Order)\
            .filter(Order.actor == strategy_actor)\
            .filter(Trade.trade_type == trade_type)\
            .filter(Trade.time_created < start_time)\
            .options(joinedload('order'))\
            .order_by(Trade.time_created.desc())

        if open_position_trades:
            # Filter out trades we already got.
            query = query.filter(
                ~Trade.unique_id.in_([t.unique_id for t in open_position_trades])
            )  

        trades_batch = query.limit(10).all()

        for trade in trades_batch:
            if (sum([t.volume for t in open_position_trades]) 
                    < abs(open_position_offset)):
                open_position_trades.append(trade)

    total_volume = sum([t.volume for t in open_position_trades])

    # This is the amount to trim off the last trade.
    volume_to_trim = total_volume - abs(open_position_offset)
    last_trade = open_position_trades.pop()

    # Copy it so we're not modifying a db object.
    last_trade = copy_trade(last_trade)
    volume_to_keep = last_trade.volume - volume_to_trim

    # Price and fee are absolutes, not per-bitcoin, so we need to trim them as well.
    ratio = volume_to_keep / last_trade.volume
    last_trade.volume *= ratio
    last_trade.price *= ratio
    last_trade.fee *= ratio

    open_position_trades.append(last_trade)

    # Flip these around so oldest are first like the rest of our trades.
    open_position_trades.reverse()

    return open_position_trades


def exchange_profit_participation(profit_units):
    """
    Given a list of profit units, returns a dictionary with the percentage of the total
    profit that was gained from trading on each exchange.
    """
    exchange_absolute_profits = defaultdict(lambda: Money(0, 'USD'))

    # This is multiplied by two because every dollar of profit is attributed to two
    # exchanges, therefore to get percentages that add up to 100 we have to count every
    # dollar twice. It works.
    total_profit = sum([unit['profit'] for unit in profit_units])

    for unit in profit_units:
        for exchange_name in unit['exchanges']:
            exchange_profit = exchange_absolute_profits[exchange_name]

            exchange_profit += unit['profit'] / 2

            exchange_absolute_profits[exchange_name] = exchange_profit

    exchange_percentage_profits = {}

    for exchange_name, exchange_profit in exchange_absolute_profits.items():
        exchange_percentage_profits[exchange_name] = exchange_profit / total_profit

    return exchange_percentage_profits


def rsb(revenue, total_volume):
    real_spread_per_bitcoin = None

    if total_volume > 0:
        real_spread_per_bitcoin = (revenue.amount) / total_volume.amount

    return real_spread_per_bitcoin


def fsb(profit, total_volume):
    fee_spread_per_bitcoin = None

    if total_volume > 0:
        fee_spread_per_bitcoin = (profit.amount) / total_volume.amount

    return fee_spread_per_bitcoin
