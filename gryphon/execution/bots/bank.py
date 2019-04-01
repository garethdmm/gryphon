import os
import subprocess
import time

import termcolor as tc

from gryphon.execution.lib.heartbeat import heartbeat
from gryphon.execution.bots import shoebox
from gryphon.lib import session
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.logger import get_logger
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.scrapers.base import Scraper
from gryphon.lib.scrapers.bmo import BMOScraper
from gryphon.lib.scrapers.boa import BoAScraper
from gryphon.lib.slacker import Slacker
from gryphon.lib.util.time import humanize_seconds

logger = get_logger(__name__)

TICK_SLEEP = 60 * 60  # 1 hour
BURN_THRESHOLD = 10000

BANK_AUDIT_HEARTBEAT_KEY = 'BANK_AUDIT_%s'


def run():
    db = session.get_a_trading_db_mysql_session()

    try:
        logger.info('Reporting for duty.')

        while True:
            audit_bmo_accounts(db)
            audit_boa_accounts(db)

            session.commit_mysql_session(db)
            logger.info('Going to sleep for %s.' % humanize_seconds(TICK_SLEEP))
            time.sleep(TICK_SLEEP)

    finally:
        db.remove()


def audit_bmo_accounts(db):
    scraper = BMOScraper()
    audit_bank_accounts(db, scraper)
    scraper.quit()


def audit_boa_accounts(db):
    scraper = BoAScraper()
    audit_bank_accounts(db, scraper)
    scraper.quit()


def audit_bank_accounts(db, scraper):
    """
    Check the balances of each bank account. If they differ, look for and add the new transactions.

    Writes BANK_AUDIT_<key> heartbeats on success.
    """
    try:
        account_data = scraper.load()
    except Scraper.MaintenanceException as e:
        # The heartbeats will fail, but the audit will retry every hour.
        scraper_name = scraper.__class__.__name__
        logger.info(tc.colored('%s: Service Unavailable' % scraper_name, 'yellow'))

        msg = str(e)
        if msg:
            logger.info(tc.colored(msg, 'yellow'))

        return

    for account in account_data:
        account_num = account['account_number']
        account_key = account_num_to_key(account_num)

        db_account = exchange_factory.make_exchange_data_from_key(account_key, db)

        db_balance = db_account.balance.fiat()
        ledger_balance = db_account.ledger_balance().fiat()

        if ledger_balance != db_balance:
            msg = 'DB balance: %s != Ledger balance: %s' % (db_balance, ledger_balance)
            logger.info(tc.colored(msg, 'red'))
            return

        bank_balance = account['balance']

        if bank_balance == db_balance:
            success(account_key)
        else:
            balance_diff = bank_balance - db_balance
            transactions = scraper.load_transactions(account_num)

            new_transactions = find_new_transactions(transactions, balance_diff)
            record_transactions(db_account, new_transactions, db)

            db_balance = db_account.balance.fiat()
            if bank_balance == db_balance:
                success(account_key)
            else:
                msg = 'Our balance: %s != Bank balance: %s' % (db_balance, bank_balance)
                logger.info(tc.colored(msg, 'red'))


def find_new_transactions(transactions, balance_diff):
    """
    Find the latest n transactions which caused our balance to change by <balance_diff>.
    """
    if balance_diff.amount == 0:
        return []

    logger.debug('looking for new transactions to match a %s diff' % balance_diff)

    running_total = 0
    new_transactions = []
    for transaction in reversed(transactions):
        amount = transaction['amount']
        if transaction['type'] == Transaction.WITHDRAWL:
            amount = -amount

        running_total += amount

        logger.debug('found a transaction for %s' % amount)
        new_transactions.append(transaction)

        # TODO: Once we have been running the bank auditor for a bit and have good data,
        # we probably also want to make sure that the most recent db transaction matches the
        # next oldest transaction from BMO.
        #
        # most_recent_db_transaction = bmo_usd_db.transactions\
        #     .filter(Transaction.transaction_status == Transaction.COMPLETED)\
        #     .order_by(Transaction.time_completed.desc())\
        #     .first()
        # if do_transactions_match(most_recent_db_transaction, transaction)

        if running_total == balance_diff:
            return new_transactions

    return []


def do_transactions_match(db_transaction, bank_transaction):
    """
    Check if a transaction from our database matches a transaction from the bank scraper.
    """
    return (
        db_transaction.transaction_details['description'] == bank_transaction['description'] and
        db_transaction.transaction_type == bank_transaction['type'] and
        db_transaction.amount == bank_transaction['amount']
    )


def record_transactions(db_account, transactions, db):
    """
    Record any new transactions found in our bank account.

    This fall into 3 categories:
    1. Expected pending deposits (wires from exchanges)
    2. Unexpected deposits (reverse burn)
    3. Unexpected withdrawals (burn)

    Expected withdrawals (wires to exchanges) are handled by manual withdrawals
    done from the command line by the person doing money-moving.
    """
    for transaction in transactions:
        if transaction['type'] == Transaction.DEPOSIT:
            pending_deposit = db_account.deposit_landed(transaction['amount'])
            if pending_deposit:
                logger.info(tc.colored('Recorded pending deposit for %s [%s]' % (transaction['amount'], transaction['description']), 'green'))
                notify_on_call_dev(transaction, db_account)
                continue
            elif transaction['amount'] < BURN_THRESHOLD:
                record_reverse_burn(db_account, transaction, db)
                logger.info(tc.colored('Recorded reverse burn for %s [%s]' % (transaction['amount'], transaction['description']), 'green'))
        elif transaction['type'] == Transaction.WITHDRAWL:
            # Sanity check (burn transactions should be under $10,000)
            if transaction['amount'] < BURN_THRESHOLD:
                record_burn(db_account, transaction, db)
                logger.info(tc.colored('Recorded burn for %s [%s]' % (transaction['amount'], transaction['description']), 'green'))


def notify_on_call_dev(transaction, db_account):
    """
    Notify the current on-call dev that a wire has landed
    """
    try:
        on_call_dev = shoebox.get_on_call_dev()
        channel = '@%s' % on_call_dev

        message = '%s wire landed in %s [%s]' % (transaction['amount'], db_account.name, transaction['description'])

        slacker = Slacker(channel, 'mover', icon_emoji=':moneybag:')
        slacker.notify(message)
    except:
        pass


def record_burn(db_account, transaction, db):
    """
    Record transactions which "unexpectedly" took money out of our bank account.

    We expect this for burn: payroll, rent, bills, etc.
    """
    if transaction['type'] != Transaction.WITHDRAWL:
        raise ValueError('Burn must be a withdrawal')

    amount = transaction['amount']

    transaction_details = {}
    transaction_details['description'] = transaction['description']

    burn_account = exchange_factory.make_exchange_data_from_key('BURN', db)

    deposit, __ = db_account.record_fiat_withdrawal(
        burn_account,
        amount,
        transaction_details=transaction_details,
    )
    deposit.complete()


def record_reverse_burn(db_account, transaction, db):
    """
    Record transactions which "unexpectedly" put money back into our bank account.

    We expect this for interest, Matinee payments, reversed bank errors, etc.
    """
    if transaction['type'] != Transaction.DEPOSIT:
        raise ValueError('Reverse burn must be a deposit')

    amount = transaction['amount']

    transaction_details = {}
    transaction_details['description'] = transaction['description']

    burn_account = exchange_factory.make_exchange_data_from_key('BURN', db)

    deposit, __ = burn_account.record_fiat_withdrawal(
        db_account,
        amount,
        transaction_details=transaction_details,
    )
    deposit.complete()


def account_num_to_key(account_num):
    """
    Convert from BMO account number to exchange database key.

    eg: '2423 xxxx-xxx' -> 'BMO_USD'
    Requires the <KEY>_ACCOUNT_NUMBER env vars to be set.
    """
    accounts_map = load_accounts_map()
    reverse_map = {num: key for key, num in accounts_map.items()}

    return reverse_map[account_num]


def key_to_account_num(key):
    """
    Convert from exchange database key to BMO account number.

    eg: 'BMO_USD' -> '2423 xxxx-xxx'
    Requires the <KEY>_ACCOUNT_NUMBER env vars to be set.
    """
    accounts_map = load_accounts_map()

    return accounts_map[key]


def load_accounts_map():
    accounts_map = {}

    for key in exchange_factory.BANK_ACCOUNT_KEYS:
        env_name = '%s_ACCOUNT_NUMBER' % key
        account_num = os.environ[env_name]
        accounts_map[key] = account_num

    return accounts_map


def success(name):
    logger.info(tc.colored('%s passed the audit' % name, 'green'))
    heartbeat(BANK_AUDIT_HEARTBEAT_KEY % name)
