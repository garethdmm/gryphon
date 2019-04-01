"""
This script sets up an exchange, or set of exchanges, for trading in your gryphon
database.

To trade with an exchange in Gryphon, we need to start a ledger of trades and
transactions for that exchange. In the current database, a ledger is simply an entry
in the Exchange table that is referenced by entries in the Order, Trade, and
Transaction tables.

For us to start trading we need to create that entry in the Exchange table, and add two
dummy transactions that represent the starting balance of the exchange.

Usage:
    gryphon-execute script initialize_exchange_ledger
        --exchanges [comma-separated list of exchange pairs, e.g. bitstamp_btc_usd]
        [--execute]
"""

import pyximport; pyximport.install()

import os

from gryphon.lib import configuration
from gryphon.lib import session
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money


ALREADY_INITIALIZED_ERR_MESSAGE = """\
Unable to initialize %s, there is already a db entry for that exchange name.\
"""

NO_API_CREDENTIALS_ERR_MESSAGE = """\
Could not initialize %s because we couldn't find API credentials for it.\
"""

UNKNOWN_ERR_MESSAGE = """\
Could not initialize %s, for an unexpected reason.\
"""

INITIALIZATION_TX_NOTES = """Initializing the db's %s balance"""


def initialize_exchange_ledger(db, wrapper_obj):
    db_obj = None

    try:
        db_obj = wrapper_obj.exchange_account_db_object(db)
    except AssertionError:
        # This is fine, the above line is supposed to fail.
        pass
    finally:
        if db_obj is not None:
            print ALREADY_INITIALIZED_ERR_MESSAGE % wrapper_obj.name
            return

    # Create the entry in the Exchange table.
    db_obj = ExchangeData(wrapper_obj.name)

    # Proceed to creating initializing transactions.
    price_currency = wrapper_obj.currency
    vol_currency = wrapper_obj.volume_currency

    try:
        balance = wrapper_obj.get_balance()
    except KeyError as e:
        print NO_API_CREDENTIALS_ERR_MESSAGE % wrapper_obj.name
        print e
        return
    except Exception as e:
        print UNKNOWN_ERR_MESSAGE % wrapper_obj.name
        print e
        return

    price_currency = wrapper_obj.currency
    vol_currency = wrapper_obj.volume_currency

    price_currency_balance = balance[price_currency]
    price_tx_details = {
        'notes': INITIALIZATION_TX_NOTES % price_currency,
    }

    vol_currency_balance = balance[vol_currency]
    vol_tx_details = {
        'notes': INITIALIZATION_TX_NOTES % vol_currency,
    }

    price_currency_tx = Transaction(
        Transaction.DEPOSIT,
        Transaction.IN_TRANSIT,
        price_currency_balance,
        db_obj,
        transaction_details=price_tx_details,
        fee=Money('0', price_currency),
    )

    vol_currency_tx = Transaction(
        Transaction.DEPOSIT,
        Transaction.IN_TRANSIT,
        vol_currency_balance,
        db_obj,
        transaction_details=vol_tx_details,
        fee=Money('0', vol_currency),
    )

    db.add(db_obj)
    db.add(price_currency_tx)
    db.add(vol_currency_tx)

    price_currency_tx.complete()
    vol_currency_tx.complete()


def main(script_arguments, execute):
    exchanges = configuration.parse_configurable_as_list(script_arguments['exchanges'])

    db = session.get_a_trading_db_mysql_session()

    for exchange_name in exchanges:
        exchange_wrapper = exchange_factory.make_exchange_from_key(exchange_name)
        initialize_exchange_ledger(db, exchange_wrapper)

    if execute is True:
        db.commit()

