"""
This script modifies the database object and ledger for an exchange to bring both in
line with the exchange API's reported balance for this account.

It does this by calculating forcing exchange_account.balance to equal ledger_balance,
and then adding arbitrary deposit or withdrawal transactions to the ledger to make
the ledger match what the exchange API reports.

This is NOT intended to be used except on test databases or in extraordinary
circumstances. Adding arbitrary adjustments to the ledger can cause serious problems for
your business down the line.

This script does not wipe the trade or transaction history.

TODO: We need better language for the 'balance' field on the ExchangeData/Exchange
account database object. It's really just a cache.
"""

import pyximport; pyximport.install()

import os
import sys

from gryphon.lib import session
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.logger import get_logger
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money

logger = get_logger(__name__)

FIX_DESCRIPTION = "\nOur record of %s\'s %s balance is off from what the exchange reports by %s. We will add an arbitrary %s for %s to bring our ledger back into agreement with the exchange."


def align_ledger_and_balance_cache_for_exchange_account_in_currency(db, exchange, currency, execute):
    """
    The first step to fixing a balance mismatch between an exchange and the gryphon db
    is to make sure that the ledger balance (calculated from trades and transactions)
    equals the 'balance' field on the exchange account object.
    """
    exchange_account = exchange.exchange_account_db_object(db)

    ledger_balance = exchange_account.ledger_balance()

    if exchange_account.balance[currency] != ledger_balance[currency]:
        exchange_account.balance[currency] = ledger_balance[currency]

        logger.info(
            'Updated the balance cache for db to match the ledger in currency %s.' % (
            currency,
        ))

        db.add(exchange_account)
    else:
        logger.info('%s balance cache is in line with the ledger.' % currency)


def align_ledger_and_exchange_balance_in_currency(db, exchange, exchange_balance, currency, execute):
    exchange_account = exchange.exchange_account_db_object(db)
    db_balance = exchange_account.balance
    ledger_balance = exchange_account.ledger_balance()

    mismatch = ledger_balance[currency] - exchange_balance[currency]

    tx = None
    tx_amount = abs(mismatch)
    tx_type = None

    # Create the transactions.
    if mismatch < 0:  # Our db balance is too low, record a desposit.
        tx_type = Transaction.DEPOSIT
    elif mismatch > 0:  # Our db balance too high, record a withdrawal.
        tx_type = Transaction.WITHDRAWL
    else:
        logger.info('%s balance is good, nothing do to.' % currency)
        return

    if tx_type is not None:
        tx = Transaction(
            tx_type,
            Transaction.IN_TRANSIT,
            tx_amount,
            exchange_account,
            transaction_details={'notes': 'Arbitrary ledger adjustment.'},
            fee=Money('0', currency),
        )

        logger.info(
            FIX_DESCRIPTION % (
            exchange.name,
            currency,
            mismatch,
            'deposit' if tx_type == Transaction.DEPOSIT else 'withdrawal',
            tx_amount,
        ))

    db.add(tx)
    tx.complete()


def reset_balance_for_exchange_in_currency(db, exchange, exchange_balance, currency, execute=False):
    """
    This function brings the database balance (exchange_account.balance) in line with
    the ledger balance, and then adds transactions as necessary to bring the ledger
    balance in line with the exchange balance.
    """
    align_ledger_and_balance_cache_for_exchange_account_in_currency(
        db,
        exchange,
        currency,
        execute,
    )

    align_ledger_and_exchange_balance_in_currency(
        db,
        exchange,
        exchange_balance,
        currency,
        execute,
    )

    if execute is True:
        db.commit()
        logger.info('Committed')
    else:
        logger.info('Not committing because execute=False')


def fix_balance_issues_for_exchange(exchange_name, execute=False):
    db = session.get_a_trading_db_mysql_session()
    exchange = exchange_factory.make_exchange_from_key(exchange_name)

    if not exchange:
        raise Exception('No exchange %s' % exchange_name)

    exchange_balance = exchange.get_balance()

    reset_balance_for_exchange_in_currency(
        db,
        exchange,
        exchange_balance,
        exchange.currency,
        execute,
    )

    reset_balance_for_exchange_in_currency(
        db,
        exchange,
        exchange_balance,
        exchange.volume_currency,
        execute,
    )


def main(script_arguments, execute):
    exchange_name = script_arguments['exchange_name']

    fix_balance_issues_for_exchange(exchange_name, execute)

