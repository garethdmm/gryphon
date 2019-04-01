import termcolor as tc
import time

from gryphon.execution.strategies.base import Strategy
from gryphon.execution.lib.exchange_color import exchange_color
from gryphon.lib import session
from gryphon.lib.exchange.exchange_factory import *
from gryphon.lib.money import Money
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


def get_target(exchange_name):
    db = session.get_a_trading_db_mysql_session()
    try:
        exchange = make_exchange_from_key(exchange_name)
        exchange_data = exchange.exchange_account_db_object(db)
        if not exchange_data:
            exchange_data = ExchangeData(exchange.name)
        target = exchange_data.target['BTC']
        logger.info("%s's target is %s", exchange.friendly_name, target)
    finally:
        db.remove()
    return target

def change_target(exchange_name, target_delta):
    db = get_a_trading_db_mysql_session()

    try:
        exchange = make_exchange_from_key(exchange_name)
        exchange_data = exchange.exchange_account_db_object(db)

        if not exchange_data:
            exchange_data = ExchangeData(exchange.name)

        amount = Money(target_delta, "BTC")
        orig_amount = exchange_data.target[amount.currency]
        exchange_data.target[amount.currency] += amount
        db.add(exchange_data)
        commit_mysql_session(db)

        logger.info("Changed %s target from %s to %s", exchange.friendly_name, orig_amount, exchange_data.target[amount.currency])

    finally:
        db.remove()
