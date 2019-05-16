"""
Gryphon Command Line Interface.
===

This is a simple file that is used to create a custom python console with lots of useful
imports and database or exchange connections already available to the user. It's
available as soon as you install gryphon through the command line with:
    gryphon-cli

Note that to use the gryphon console you should have a .env in your current working
directory. That provides the necessary credentials for any connections you want to use.
For this reason we recommend habitually only starting the console from a single
directory, which might be the same directory that you keep your trading .env file and
strategy config files.
"""

import pyximport; pyximport.install()

from datetime import datetime, timedelta
import logging

from cdecimal import *

from gryphon.lib import environment
from gryphon.lib import session
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.logger import get_logger
from gryphon.lib.money import Money
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.models.event import Event
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.models.liability import Liability
from gryphon.lib.time_parsing import parse

# There's a bizarre bug I haven't had time to investigate whereby if we import
# Delorean in order with the rest of the 3rd party libaries, our time_parsing lib
# doesn't work. This only happens in the console. Bizarre.
from delorean import Delorean

logger = get_logger(__name__)

NO_GDS_ERROR = """\
Couldn't get a gds session. Probably missing credentials or GDS isn't set up.\
"""

# Load the contents of the .env.
environment.load_environment_variables()

# Create oft-used database objects.
trading_db = session.get_a_trading_db_mysql_session()

try:
    gds_db = session.get_a_gds_db_mysql_session()
except Exception as e:
    logger.info(NO_GDS_ERROR)


# Create the oft-used exchange connection shortcuts.
console_shortcuts = {
  'COINBASE_BTC_USD': 'cb',
  'BITSTAMP_BTC_USD': 'b',
  'BITSTAMP_BTC_EUR': 'be',
  'BITSTAMP_BCH_USD': 'bbch',
  'BITSTAMP_BCH_EUR': 'bbche',
  'BITSTAMP_BCH_BTC': 'bbchb',
  'BITSTAMP_ETH_EUR': 'bee',
  'BITSTAMP_ETH_USD': 'beu',
  'BITSTAMP_ETH_BTC': 'beb',
  'GEMINI_BTC_USD': 'g',
  'GEMINI_ETH_USD': 'geu',
  'GEMINI_ETH_BTC': 'geb',
  'GEMINI_LTC_USD': 'glu',
  'GEMINI_ZEC_USD': 'gzu',
  'ITBIT_BTC_USD': 'i',
  'KRAKEN_BTC_USD': 'k',
  'KRAKEN_BTC_EUR': 'k_eur',
  'KRAKEN_BTC_CAD': 'k_cad',
}

exchanges = {}

exchange_wrappers = exchange_factory.get_all_initialized_exchange_wrappers(trading_db)

for exchange in exchange_wrappers:
    if exchange.name in console_shortcuts.keys():
        shortcut_name = console_shortcuts[exchange.name]
        globals()[shortcut_name] = exchange
        exchanges[shortcut_name] = exchange


def main():
    from IPython import embed

    embed()


if __name__ == '__main__':
    main()

