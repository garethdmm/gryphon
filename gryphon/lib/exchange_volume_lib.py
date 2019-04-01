"""
These functions handle getting exchange volume numbers from the three different volume
data sources we have. These sources, listed in order of our preference, are:
i) Daily exchange ticker entries saved in ourd database
ii) Exchange trade lists saved in our database
iii) The Bitcoinwisdom API

The main interface of this library is get_single_exchange_volume_in_period and
get_total_exchange_volume_in_period. These two functions  decide which source to use
for a given time period and route the call the other functions in this file.
"""

from datetime import datetime, timedelta

from delorean import Delorean
from sqlalchemy import distinct, func

from gryphon.lib.bitcoinwisdom import BitcoinWisdom
from gryphon.lib.exchange.exchange_factory import ALL_EXCHANGE_KEYS
from gryphon.lib.models.emeraldhavoc.exchange_volume import ExchangeVolume
from gryphon.lib.models.emeraldhavoc.trade import Trade as EHTrade
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

# this is a hack for now because we don't have consistent data
# sources for the other exchanges, and I don't want to dirty
# gryphon.lib's commit history with something like this.
exchanges_with_volume_sources = [
    'cavirtex', 
    'kraken', 
    'bitstamp', 
    'bitfinex', 
    'vaultofsatoshi',
]

EARLIEST_TICKER_ENTRY = parse('2015-11-13 19:30').datetime
EARLIEST_TRADE_ENTRY = parse('2015-11-25 23:59').datetime


# Functions for getting a single exchange's volume

def get_single_exchange_volume_in_period(tc_db, exchange_name, start_time, end_time):
    if is_past_single_day(start_time, end_time) and start_time > EARLIEST_TICKER_ENTRY:
        return get_single_exchange_volume_on_day_from_db_tickers(
            tc_db,
            exchange_name,
            start_time,
        )
    elif start_time > EARLIEST_TRADE_ENTRY:
        return get_single_exchange_volume_in_period_from_db_trades(
            tc_db,
            exchange_name,
            start_time,
            end_time,
        )
    elif exchange_name in exchanges_with_volume_sources:
        return get_single_exchange_volume_from_bitcoinwisdom(
            exchange_name,
            start_time,
            end_time,
        )
    else:
        return None


def get_single_exchange_volume_from_bitcoinwisdom(exchange_name, start_time, end_time):
    bw = BitcoinWisdom(exchange=exchange_name.lower())

    return bw.volume_in_period(
        start_time,
        end_time,
    )


def get_single_exchange_volume_on_day_from_db_tickers(tc_db, exchange_name, day_start):
    """
    Get the exchange volume for this exchange on a particular day from our saved
    ticker data.
    """

    # This is slightly counterintuitive. The volume for day x is in the first saved
    # ticker on day x + 1. So we look for that ticker.
    day_end = day_start + timedelta(days=1)
    five_minutes_later = day_end + timedelta(minutes=5)

    exchange_volume_obj = tc_db.query(ExchangeVolume)\
        .filter(ExchangeVolume.timestamp > day_end)\
        .filter(ExchangeVolume.timestamp < five_minutes_later)\
        .filter(ExchangeVolume.exchange == exchange_name)\
        .first()

    if not exchange_volume_obj:
        return None
    else:
        return exchange_volume_obj.exchange_volume


def get_single_exchange_volume_in_period_from_db_trades(tc_db, exchange_name, start_time, end_time):
    """
    Get the exchange volume for this exchange in this period from our saved version
    of the trade history.
    """

    total_volume = tc_db.query(func.sum(EHTrade._volume))\
        .filter(EHTrade.timestamp >= start_time)\
        .filter(EHTrade.timestamp < end_time)\
        .filter(EHTrade.exchange == exchange_name)\
        .scalar()

    return Money(total_volume, 'BTC')


# Functions for getting all integrated exchanges' volume in a period.

def get_total_exchange_volume_in_period(tc_db, start_time, end_time):
    if is_past_single_day(start_time, end_time) and start_time > EARLIEST_TICKER_ENTRY:
        return get_total_exchange_volume_on_day_from_db_tickers(tc_db, start_time)
    elif start_time > EARLIEST_TRADE_ENTRY:
        return get_total_exchange_volume_in_period_from_db_trades(
            tc_db,
            start_time,
            end_time,
        )
    else:
        return get_total_exchange_volume_from_bitcoinwisdom(
            start_time,
            end_time,
        )


def get_total_exchange_volume_on_day_from_db_tickers(tc_db, day_start):
    total_exchange_volume = Money(0, 'BTC')
    included_exchanges = []

    for exchange_name in ALL_EXCHANGE_KEYS:
        single_exchange_volume = get_single_exchange_volume_on_day_from_db_tickers(
            tc_db,
            exchange_name,
            day_start,
        )

        if single_exchange_volume:
            included_exchanges.append(exchange_name)
            total_exchange_volume += single_exchange_volume

    return total_exchange_volume, included_exchanges


def get_total_exchange_volume_from_bitcoinwisdom(start_time, end_time):
    total_exchange_volume = Money(0, 'BTC')
    included_exchanges = []

    for exchange_name in exchanges_with_volume_sources:
        single_exchange_volume = get_single_exchange_volume_from_bitcoinwisdom(
            exchange_name,
            start_time, 
            end_time,
        )

        if single_exchange_volume:
            included_exchanges.append(exchange_name)
            total_exchange_volume += single_exchange_volume

    return total_exchange_volume, included_exchanges


def get_total_exchange_volume_in_period_from_db_trades(tc_db, start_time, end_time):
    """
    Get the exchange volume for this exchange in this period from our saved version
    of the trade history.
    """

    # Watch this query for performance.
    results = tc_db.query(
            EHTrade.exchange,
            func.sum(EHTrade._volume),
        )\
        .filter(EHTrade.timestamp >= start_time)\
        .filter(EHTrade.timestamp < end_time)\
        .group_by(EHTrade.exchange)\
        .all()

    included_exchanges = [e[0].lower() for e in results]
    total_volume = sum([e[1] for e in results])

    return Money(total_volume, 'BTC'), included_exchanges


def get_hourly_total_exchange_volume_in_period(tc_db, start_time, end_time):
    return get_hourly_total_exchange_volume_in_period_from_db_trades(
        tc_db,
        start_time,
        end_time,
    )

def get_hourly_total_exchange_volume_in_period_from_db_trades(tc_db, start_time, end_time):
    """
    Get the exchange volume for this exchange in this period from our saved version
    of the trade history.
    """

    # Watch this query for performance.
    results = tc_db.query(
            func.hour(EHTrade.timestamp),
            func.sum(EHTrade._volume),
        )\
        .filter(EHTrade.timestamp >= start_time)\
        .filter(EHTrade.timestamp < end_time)\
        .group_by(func.hour(EHTrade.timestamp))\
        .all()

    formatted_results = []

    for row in results:
        hour = row[0]
        timestamp = Delorean(start_time, 'UTC').next_hour(hour).datetime
        volume = Money(row[1], 'BTC')

        formatted_results.append([
            timestamp,
            volume,
        ])

    formatted_results = sorted(formatted_results, key=lambda r: r[0])

    return formatted_results


def get_hourly_single_exchange_volume_in_period(tc_db, exchange_name, start_time, end_time):
    """
    We technically do have historical trade data now, but it's not proven yet so
    we're ignoring it until it is.
    """
    return get_hourly_single_exchange_volume_in_period_from_db_trades(
        tc_db,
        exchange_name,
        start_time,
        end_time,
    )


def get_hourly_single_exchange_volume_in_period_from_db_trades(tc_db, exchange_name, start_time, end_time):
    """
    Get the exchange volume for this exchange in this period from our saved version
    of the trade history.
    """

    # Watch this query for performance.
    results = tc_db.query(
            func.hour(EHTrade.timestamp),
            func.sum(EHTrade._volume),
        )\
        .filter(EHTrade.timestamp >= start_time)\
        .filter(EHTrade.timestamp < end_time)\
        .filter(EHTrade.exchange == exchange_name)\
        .group_by(func.hour(EHTrade.timestamp))\
        .all()

    formatted_results = []

    for row in results:
        hour = row[0]
        timestamp = Delorean(start_time, 'UTC').next_hour(hour).datetime
        volume = Money(row[1], 'BTC')

        formatted_results.append([
            timestamp,
            volume,
        ])

    formatted_results = sorted(formatted_results, key=lambda r: r[0])

    return formatted_results


def is_past_single_day(start_time, end_time):
    return (start_time.hour == 0) and (end_time - start_time == timedelta(days=1)) and end_time < Delorean().datetime


