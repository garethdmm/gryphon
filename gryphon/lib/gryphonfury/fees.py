from collections import defaultdict

from sqlalchemy import func

from gryphon.lib.logger import get_logger
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.models.exchange import Exchange, Balance
from gryphon.lib.money import Money

logger = get_logger(__name__)

def get_all_fees_in_period_by_exchange_in_usd(db, start, end):
    fees_by_exchange = db\
        .query(
            func.sum(Trade.fee_in_usd),
            Order._exchange_name,
        )\
        .join(Order)\
        .filter(Trade.time_created >= start)\
        .filter(Trade.time_created < end)\
        .group_by(Order._exchange_name)\
        .all()

    exchange_fees = defaultdict(lambda: Money(0, 'USD'))

    for fees, exchange_name in fees_by_exchange:
        exchange_fees[exchange_name] = Money(fees, 'USD')

    return exchange_fees

def get_all_fees_in_period_in_usd(db, start, end):
    fees = db\
        .query(func.sum(Trade.fee_in_usd))\
        .join(Order)\
        .filter(Trade.time_created >= start)\
        .filter(Trade.time_created < end)\
        .scalar()

    if fees is not None:
        fees = Money(fees, 'USD')
    else:
        fees = Money(0, 'USD')

    return fees

def get_wire_fees_in_period_by_currency(db, start, end):
    wire_fee_results = db\
        .query(Transaction._fee_currency, func.sum(Transaction._fee))\
        .filter(Transaction.time_created >= start)\
        .filter(Transaction.time_created < end)\
        .filter(Transaction._fee != None)\
        .group_by(Transaction._fee_currency)\
        .all()

    wire_fees = Balance()

    for fee_currency, fee_amount in wire_fee_results:
        wire_fees[fee_currency] = Money(fee_amount, fee_currency)

    return wire_fees


def get_all_wire_fees_in_period_in_usd(db, start, end):
    fees_by_currency = get_wire_fees_in_period_by_currency(db, start, end)

    return fees_by_currency.total_usd_value()


def get_wire_fees_in_period_by_exchange(db, start, end):
    wire_fee_results = db\
        .query(
            Transaction._fee_currency,
            func.sum(Transaction._fee),
            Exchange.name,
        )\
        .join(Exchange)\
        .filter(Transaction.time_created >= start)\
        .filter(Transaction.time_created < end)\
        .filter(Transaction._fee != None)\
        .group_by(Exchange.name, Transaction._fee_currency)\
        .all()

    wire_fees = {}

    for fee_currency, fee_amount, exchange_name in wire_fee_results:
        wire_fees[exchange_name] = Money(fee_amount, fee_currency)

    return wire_fees

def get_matched_trading_fees_in_period(db, start_time, end_time):
    """
    This function gives you total trading fees for trades who's p&l was realized in
    the period under question. This means that fees to open the position at the
    beginning of this period are included, and fees to open the position at the end
    of the period are removed.
    """

    fees = get_all_fees_in_period_in_usd(db, start_time, end_time)

    start_position, end_position = get_start_and_end_position(db, start_time, end_time)

    start_open_position_trades, end_open_position_trades = get_start_and_end_position_trades(db, start_time, end_time, start_position, end_position)

    start_position_fee = sum(
        [t.fee_in_usd for t in start_open_position_trades]
    )

    end_position_fee = sum(
        [t.fee_in_usd for t in end_open_position_trades]
    )

    fees = fees + start_position_fee
    fees = fees - end_position_fee

    return fees
