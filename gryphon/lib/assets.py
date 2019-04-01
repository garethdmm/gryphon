from collections import namedtuple

from cdecimal import Decimal
from delorean import Delorean
from sqlalchemy import func, or_, and_

from gryphon.lib.exchange import exchange_factory
from gryphon.lib.gryphonfury import positions
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.models.exchange import Position
from gryphon.lib.models.liability import Liability
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse

logger = get_logger(__name__)

# If your ledger is only accurate after a certain time, put it here, and ledger_balance
# requests earlier than this will throw an exception.
EARLIEST_CORRECT_LEDGER_DATE = parse('2015-01-01').datetime


# This number is used by the overwatch bot to determine if there is a bitcoin amount
# missing from our system.
# TODO:
#   - This should be configurable by the user. Since this is only used in overwatch,
#     maybe it should be part of an overwatch config.
#   - We should also be able to represent targets in all our supported cryptocurrencies
#     in this manner.
BTC_NET_ASSETS_TARGET = Money('0', 'BTC')

NO_BURN_ACCOUNT_WARNING = """\
There is no entry with the name 'BURN' in your exchange account table, so we won't\
be able to show non-trading expenses in the dashboard service. You can learn how to\
set this feature up in the framework documentation.\
"""


def get_all_liabilities(trading_db):
    liabilities = trading_db.query(Liability).all()
    return liabilities


def get_active_liabilities(trading_db, date=Delorean().naive):
    debts = get_all_liabilities(trading_db)
    active_debts = []

    # Annoying that this is still necessary.
    date = date.replace(tzinfo=None)

    for debt in debts:
        # an active debt started before the current date
        # and either has not been repaid, or was repaid after the current date

        if (debt.time_started <= date
                and (not debt.time_repayed or debt.time_repayed > date)):
            active_debts.append(debt)

    return active_debts


def get_active_btc_liabilities(trading_db):
    active_liabilities = get_active_liabilities(trading_db)
    active_btc_liabilities = [
        l for l in active_liabilities if l.amount.currency == 'BTC'
    ]
    return active_btc_liabilities


def calculate_btc_net_assets_error(db):
    btc_net_assets = calculate_btc_net_assets(db)
    outstanding_btc_fees = calculate_outstanding_btc_fees(db)

    # outstanding btc fees will be bought back with a buyback transaction
    # so they are like future assets
    error = BTC_NET_ASSETS_TARGET - (btc_net_assets + outstanding_btc_fees)
    return error


def calculate_outstanding_btc_fees(db):
    raw_trade_btc_fees = db.query(func.sum(Trade._fee))\
        .filter(Trade.has_outstanding_btc_fee)\
        .scalar()

    raw_transaction_btc_fees = db.query(func.sum(Transaction._fee))\
        .filter(Transaction.has_outstanding_btc_fee)\
        .scalar()

    if raw_trade_btc_fees == None:
        raw_trade_btc_fees = 0
    if raw_transaction_btc_fees == None:
        raw_transaction_btc_fees = 0

    trade_btc_fees = Money(raw_trade_btc_fees, 'BTC')
    transaction_btc_fees = Money(raw_transaction_btc_fees, 'BTC')

    return trade_btc_fees + transaction_btc_fees


def calculate_btc_net_assets(db):
    exchange_datas = exchange_factory.all_exchange_datas(db)
    assets_from_balance = sum([e.balance['BTC'] for e in exchange_datas])

    # TODO: move this into some sort of common query
    pending_deposits = db.query(Transaction)\
        .filter_by(transaction_status='IN_TRANSIT')\
        .join(ExchangeData)\
        .filter(or_(
            Transaction._amount_currency == 'BTC',
            Transaction._fee_currency == 'BTC',
        ))\
        .all()

    assets_from_pending_deposits = Money(0, 'BTC')
    for pending_deposit in pending_deposits:
        # It is theoretically possible to be charged BTC fees on a fiat transaction
        # or vice versa, so we need to handle them independently
        if pending_deposit.amount.currency == 'BTC':
            assets_from_pending_deposits += pending_deposit.amount

        if pending_deposit.fee and pending_deposit.fee.currency == 'BTC':
            assets_from_pending_deposits -= pending_deposit.fee

    # We discount position by adding it as a liability
    # This cancels out its affect on our balance so our net assets aren't always
    # bouncing around.
    position = positions.cached_multi_position(db)
    liabilities_from_position = position

    bitcoin_liabilities = get_active_btc_liabilities(db)
    liabilities_from_debts = sum([l.amount for l in bitcoin_liabilities])

    logger.debug('Assets from Balance: %s' % assets_from_balance)
    logger.debug('Assets from Pending Deposits: %s' % assets_from_pending_deposits)

    logger.debug('Liabilities from Position: %s' % liabilities_from_position)
    logger.debug('Liabilities from Loans: %s' % liabilities_from_debts)

    total_assets = assets_from_balance + assets_from_pending_deposits
    total_liabilities = liabilities_from_position + liabilities_from_debts

    net_assets = total_assets - total_liabilities

    return net_assets


def ledger_balance(db, start_time=None, end_time=None, include_pending=False, exchange_names=[]):
    """
    Returns the exchange's balance as calculated from its ledger of trades and
    transactions.

    With no params specified we return the current balance.
    With end_time specified we return the balance at a historical point.
    With start_time specified we return a balance diff which can be useful for
    performance (if you know the balance on one day, you can get the next day's balance
    by only looking at that next days ledgers instead of from the beginning).
    """

    if start_time and start_time < EARLIEST_CORRECT_LEDGER_DATE:
        raise ValueError(
            'start_time must be later than %s' % EARLIEST_CORRECT_LEDGER_DATE,
        )

    if end_time and end_time < EARLIEST_CORRECT_LEDGER_DATE:
        raise ValueError(
            'end_time must be later than %s' % EARLIEST_CORRECT_LEDGER_DATE,
        )

    exchange_ids = []

    for exchange_name in exchange_names:
        exchange_data = exchange_factory.make_exchange_data_from_key(exchange_name, db)
        exchange_id = exchange_data.exchange_id
        exchange_ids.append(exchange_id)

    # Trades
    bid_prices = trade_position_query(
        db,
        Trade._price,
        Trade._price_currency,
        Trade.BID,
        start_time=start_time,
        end_time=end_time,
        exchange_names=exchange_names,
    )

    bid_volumes = trade_position_query(
        db,
        Trade._volume,
        Trade._volume_currency,
        Trade.BID,
        start_time=start_time,
        end_time=end_time,
        exchange_names=exchange_names,
    )

    ask_prices = trade_position_query(
        db,
        Trade._price,
        Trade._price_currency,
        Trade.ASK,
        start_time=start_time,
        end_time=end_time,
        exchange_names=exchange_names,
    )

    ask_volumes = trade_position_query(
        db,
        Trade._volume,
        Trade._volume_currency,
        Trade.ASK,
        start_time=start_time,
        end_time=end_time,
        exchange_names=exchange_names,
    )

    trade_fees = trade_position_query(
        db,
        Trade._fee,
        Trade._fee_currency,
        start_time=start_time,
        end_time=end_time,
        exchange_names=exchange_names,
    )

    # Transactions
    deposits = transaction_position_query(
        db,
        Transaction._amount,
        Transaction._amount_currency,
        transaction_type=Transaction.DEPOSIT,
        start_time=start_time,
        end_time=end_time,
        include_pending=include_pending,
        exchange_ids=exchange_ids,
    )

    withdrawals = transaction_position_query(
        db,
        Transaction._amount,
        Transaction._amount_currency,
        transaction_type=Transaction.WITHDRAWL,
        start_time=start_time,
        end_time=end_time,
        include_pending=include_pending,
        exchange_ids=exchange_ids,
    )

    transaction_fees = transaction_position_query(
        db,
        Transaction._fee,
        Transaction._fee_currency,
        start_time=start_time,
        end_time=end_time,
        include_pending=include_pending,
        exchange_ids=exchange_ids,
    )

    logger.debug('Bid Prices: %s' % bid_prices)
    logger.debug('Bid Volumes: %s' % bid_volumes)
    logger.debug('Ask Prices: %s' % ask_prices)
    logger.debug('Ask Volumes: %s' % ask_volumes)
    logger.debug('Trade Fees: %s' % trade_fees)

    logger.debug('Deposits: %s' % deposits)
    logger.debug('Withdrawals: %s' % withdrawals)
    logger.debug('Transaction Fees: %s' % transaction_fees)

    positive_position = sum([
        bid_volumes,
        ask_prices,
        deposits,
    ], Position())

    negative_position = sum([
        bid_prices,
        ask_volumes,
        trade_fees,
        withdrawals,
        transaction_fees,
    ], Position())

    total_position = positive_position - negative_position
    return total_position


def trade_position_query(db, amount_field, currency_field, trade_type=None, start_time=None, end_time=None, exchange_names=[]):
    """
    This sums up a trade Money field which can have multiple currencies.

    Takes an optional trade_type to filter on bids or asks

    Returns a multi-currency Position object
    """
    # Money fields in our database can be in multiple currencies
    # For example, trade fees can be in BTC or USD, so doing a simple sum doesn't work.
    # We group by the currency field, giving us a result like:
    # [('BTC', 10) ('USD', 900)]
    # We convert this to a position object and return it.
    query = db.query(currency_field, func.sum(amount_field))\
        .join(Order)\
        .group_by(currency_field)

    if trade_type:
        query = query.filter(Trade.trade_type == trade_type)

    if start_time:
        query = query.filter(Trade.time_created > start_time)

    if end_time:
        query = query.filter(Trade.time_created <= end_time)

    if exchange_names:
        # maybe join here?
        query = query.filter(Order._exchange_name.in_(exchange_names))

    result = query.all()

    return query_result_to_position(result)


def transaction_position_query(db, amount_field, currency_field, transaction_type=None, start_time=None, end_time=None, include_pending=False, exchange_ids=[]):
    """
    This sums up a transaction Money field which can have multiple currencies.

    Takes an optional transaction_type to filter on deposits or withdrawals

    Returns a multi-currency Position object
    """
    # See comment on trade_position_query above
    query = db.query(currency_field, func.sum(amount_field))

    if include_pending:
        query = query.filter(or_(
            Transaction.transaction_status == Transaction.COMPLETED,
            Transaction.transaction_status == Transaction.IN_TRANSIT,
        ))
    else:
        query = query.filter(Transaction.transaction_status == Transaction.COMPLETED)

    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    if start_time:
        # when include_pending is True we treat all transactions as being completed
        # on their creation time (i.e. instantly)
        if include_pending:
            query = query.filter(Transaction.time_created > start_time)
        else:
            query = query.filter(or_(
                and_(
                    Transaction.time_completed != None,
                    Transaction.time_completed > start_time,
                ),
                and_(
                    Transaction.time_completed == None,
                    Transaction.time_created > start_time,
                ),
            ))

    if end_time:
        if include_pending:
            query = query.filter(Transaction.time_created <= end_time)
        else:
            # We include transactions in the ledger based on when they were completed,
            # not created. This is an issue because we only started recording
            # time_completed on 2015-10-08. So for these pre-time_completed
            # transactions we use their time_created instead.
            query = query.filter(or_(
                and_(
                    Transaction.time_completed != None,
                    Transaction.time_completed <= end_time,
                ),
                and_(
                    Transaction.time_completed == None,
                    Transaction.time_created <= end_time,
                ),
            ))

    if exchange_ids:
        query = query.filter(Transaction.exchange_id.in_(exchange_ids))

    query = query.group_by(currency_field)

    result = query.all()

    return query_result_to_position(result)


def query_result_to_position(db_query_result):
    """
    Convert a query result into a multi-currency position
    """
    position = Position()
    # db_query_result looks like
    # [('BTC', Decimal('10')),
    # ('USD', Decimal('900'))]
    for row in db_query_result:
        currency = row[0]
        amount = row[1]
        if amount:
            position[currency] = Money(amount, currency)
    return position

def get_burn_transactions(db, start_time, end_time):
    """
    Get the list of transactions associated with the 'BURN' account in the databse. If
    there is no burn account, this function will return None.
    """
    burn_exchange_data = None

    try:
        burn_exchange_data = exchange_factory.make_exchange_data_from_key('BURN', db)
    except Exception as e:
        logger.info(NO_BURN_ACCOUNT_WARNING)

        return None

    burn_exchange_id = burn_exchange_data.exchange_id

    burn_transactions = db.query(Transaction)\
        .filter(Transaction.transaction_status == Transaction.COMPLETED)\
        .filter(Transaction.time_completed >= start_time)\
        .filter(Transaction.time_completed < end_time)\
        .filter(Transaction.exchange_id == burn_exchange_id)\
        .order_by(Transaction.time_completed.desc())\
        .all()

    return burn_transactions

def calculate_burn(db, start_time, end_time):
    burn = ledger_balance(
        db,
        start_time=start_time,
        end_time=end_time,
        exchange_names=['BURN'],
    )

    # TODO: make this more accurate.
    midpoint_time = start_time + (start_time - end_time) / 2
    usd_burn = burn.total_usd_value(date=midpoint_time)

    return usd_burn


def calculate_forex_flux(starting_balance, final_balance, start_time, end_time):
    average_balance = starting_balance + final_balance
    for currency in average_balance.keys():
        average_balance[currency] /= 2

    usd_value_at_start = average_balance.total_usd_value(date=start_time)
    usd_value_at_end = average_balance.total_usd_value(date=end_time)

    flux = usd_value_at_end - usd_value_at_start

    return flux

