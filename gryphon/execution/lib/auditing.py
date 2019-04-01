"""
Functions that run checks on an exchange account to verify that our ledger is consistent
with the exchange state.
"""

from cdecimal import Decimal
import termcolor as tc

from sqlalchemy.orm import joinedload

from gryphon.lib import session
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.gryphonfury import positions
from gryphon.lib.money import Money
from gryphon.lib.logger import get_logger
from gryphon.lib.models.order import Order
from gryphon.lib.models.transaction import Transaction

logger = get_logger(__name__)

# Audit type constants.
ORDER_AUDIT = 'order'
VOLUME_BALANCE_AUDIT = 'volume_balance'
FIAT_BALANCE_AUDIT = 'fiat_balance'
POSITION_CACHE_AUDIT = 'position_cache'
LEDGER_AUDIT = 'ledger'
ALL_AUDITS = [
    ORDER_AUDIT,
    VOLUME_BALANCE_AUDIT,
    FIAT_BALANCE_AUDIT,
    LEDGER_AUDIT,
]

class AuditException(Exception):
    pass


class OrderAuditException(AuditException):
    def __init__(self, exchange, failed_order_data):
        message = '[%s] %s order(s) failed the audit' % (
            exchange.name,
            len(failed_order_data),
        )

        super(OrderAuditException, self).__init__(message)
        self.exchange = exchange
        self.failed_order_data = failed_order_data
        self.message = message


def audit(exchange_key):
    db = session.get_a_trading_db_mysql_session()

    try:
        if exchange_key:
            exchange = exchange_factory.make_exchange_from_key(exchange_key)
            exchanges = [exchange]
        else:
            exchanges = exchange_factory.all_exchanges()

        for exchange in exchanges:
            open_orders = exchange.get_open_orders()
            if open_orders:
                logger.info(tc.colored(
                    'Cannot audit: there are open orders on %s' % (
                        exchange.friendly_name,
                    ),
                    'red',
                ))

                return

            exchange_data = exchange.exchange_account_db_object(db)

            try:
                order_audit(db, exchange, skip_recent=0)
                logger.info(tc.colored('Order Audit passed', 'green'))
            except OrderAuditException as e:
                logger.info(tc.colored('Order Audit: %s' % e.message, 'red'))

                for datum in e.failed_order_data:
                    logger.info(tc.colored(datum[1], 'red'))

            # Call this here so we don't call it twice in the two balance audits.
            exchange_balance = exchange.get_balance()

            try:
                volume_balance_audit(
                    exchange,
                    exchange_data,
                    exchange_balance=exchange_balance,
                )

                logger.info(tc.colored('BTC Audit passed', 'green'))
            except AuditException as e:
                logger.info(tc.colored(
                    '%s Audit: %s' % (exchange.volume_currency, e.message),
                    'red',
                ))

            try:
                fiat_balance_audit(
                    exchange,
                    exchange_data,
                    exchange_balance=exchange_balance,
                )

                logger.info(tc.colored('Fiat Audit passed', 'green'))
            except AuditException as e:
                logger.info(tc.colored('Fiat Audit: %s' % e.message, 'red'))

            try:
                position_cache_audit(db, exchange_data)
                logger.info(tc.colored('Position Cached Audit passed', 'green'))
            except AuditException as e:
                logger.info(tc.colored('Position Cached Audit: %s' % e.message, 'red'))

            try:
                ledger_audit(exchange_data)
                logger.info(tc.colored('Ledger Audit passed', 'green'))
            except AuditException as e:
                logger.info(tc.colored('Ledger Audit: %s' % e.message, 'red'))

    finally:
        session.commit_mysql_session(db)
        db.remove()


def close_enough(a, b, tolerance):
    return abs(a - b) <= tolerance


def order_audit(db, exchange, skip_recent=0, tolerance=Decimal('0')):
    audit_data = exchange.get_order_audit_data(skip_recent=skip_recent)
    exchange_order_ids = audit_data.keys()

    if not exchange_order_ids:  # No point hitting the database to check for no trades.
        return

    db_orders = db.query(Order)\
        .filter(Order._exchange_name == exchange.name)\
        .filter(Order.exchange_order_id.in_(exchange_order_ids))\
        .options(joinedload('trades'))\
        .all()

    db_order_hash = {}

    for db_order in db_orders:
        db_order_hash[db_order.exchange_order_id] = db_order.volume_filled

    failed_order_data = []

    for exchange_order_id, exchange_volume_filled in audit_data.iteritems():
        try:
            db_volume_filled = db_order_hash[exchange_order_id]

            if not close_enough(db_volume_filled, exchange_volume_filled, tolerance):
                audit_message = 'Order volume mismatch on #%s: %.8f != %.8f' % (
                    exchange_order_id,
                    exchange_volume_filled.amount,
                    db_volume_filled.amount,
                )

                failed_order_datum = (exchange_order_id, audit_message)
                failed_order_data.append(failed_order_datum)
        except KeyError:
            raise AuditException('Order #%s not found in database' % exchange_order_id)

    if failed_order_data:
        raise OrderAuditException(exchange, failed_order_data)

    return audit_data



def fiat_balance_audit(exchange, exchange_data, tolerance=Decimal('0'), execute=True, exchange_balance=None):
    """
    This and volume_balance_audit return the exact same data: the exchange's crypto and
    fiat balance.
    """

    balance_audit_data = balance_audit(
        exchange.currency,
        exchange,
        exchange_data,
        tolerance=tolerance,
        execute=execute,
        exchange_balance=exchange_balance,
    )

    return balance_audit_data


def volume_balance_audit(exchange, exchange_data, tolerance=Decimal('0'), execute=True, exchange_balance=None):
    balance_audit_data = balance_audit(
        exchange.volume_currency,
        exchange,
        exchange_data,
        tolerance=tolerance,
        execute=execute,
        exchange_balance=exchange_balance,
    )


    return balance_audit_data


def balance_audit(currency, exchange, exchange_data, tolerance=Decimal('0'), execute=True, exchange_balance=None):
    logger.debug('Auditing %s' % currency)

    if exchange_balance is None:
        exchange_balance = exchange.get_balance()

    exchange_amount = exchange_balance[currency]

    db_amount = exchange_data.balance[currency]
    db_amount = exchange.process_db_balance_for_audit(db_amount)

    # Check for incoming deposits.
    if not close_enough(db_amount, exchange_amount, tolerance):
        logger.debug('Balance audit failed, looking for pending deposits')

        balance_change = exchange_amount - db_amount
        success = exchange_data.deposit_landed(balance_change, tolerance=tolerance)

        if success:
            # Update balance to include landed deposits.
            db_amount = exchange_data.balance[currency]
        else:
            raise AuditException(
                'Our balance: %s != Exchange balance: %s' % (
                    db_amount,
                    exchange_amount,
                ))

    # If we're still not close enough after checking for incoming deposits.
    if not close_enough(db_amount, exchange_amount, tolerance):
        raise AuditException(
            'Our balance: %s != Exchange balance: %s' % (db_amount, exchange_amount),
        )

    # If we get this far, we passed the audit (maybe with some drift).
    # Drift measures our balance's departure from reality (the exchange), so a positive     # drift means we thought we had a higher balance than reality (i.e. an undocumented
    # loss).

    drift = db_amount - exchange_amount

    # If running in no-execute mode, we don't fix drift, and it is also not recorded
    # in audits.
    if execute and drift:
        record_drift(drift, exchange_data)

    return exchange_balance


def record_drift(drift, exchange_data):
    if drift > 0:
        transaction_type = Transaction.WITHDRAWL
    else:
        transaction_type = Transaction.DEPOSIT

    amount = abs(drift)

    logger.debug('Adding drift %s for %s' % (transaction_type, repr(amount)))

    drift_transaction = Transaction(
        transaction_type,
        Transaction.IN_TRANSIT,
        amount,
        exchange_data,
        {'drift': True},
    )

    drift_transaction.complete()


def balance_equality(balance_a, balance_b):
    """
    Because of how gryphon.lib.assets works currently, ledger_balance does not include
    keys for currencies which it has no transactions or trades for. This causes the
    normal dictionary equality operator to return false on a case where we really do
    have the right data. An example like this: {'USD': 50, 'BTC': 0} == {'USD': 50},
    with the latter being the ledger balance.

    It's out of scope for the current work to make modifications to the very-critical
    gryphon.lib.assets, but this is causing audits to fail on fresh databases, so we
    are fixing it here with the intention of a later fix to the core lib.
    """

    currencies = set(balance_a.keys() + balance_b.keys())

    for currency in currencies:
        if currency in balance_a and currency in balance_b:
            if balance_a[currency] == balance_b[currency]:
                continue
            else:
                return False
        elif currency not in balance_a:
            if balance_b[currency] == Money('0', currency):
                continue
            else:
                return False
        elif currency not in balance_b:
            if balance_a[currency] == Money('0', currency):
                continue
            else:
                return False

    return True


def ledger_audit(exchange_data):
    ledger_balance = exchange_data.ledger_balance()

    db_balance = exchange_data.balance

    if balance_equality(db_balance, ledger_balance) is not True:
        raise AuditException('DB balance: %s != Ledger balance: %s' % (
            db_balance,
            ledger_balance,
        ))


def position_cache_audit(db, exchange_data):
    multi_position = positions.fast_position(db, exchange_name=exchange_data.name)
    cached_position = exchange_data.multi_position_cache

    if multi_position != cached_position:
        raise AuditException('Cached position: %s != DB position: %s' % (
            cached_position, multi_position,
        ))

