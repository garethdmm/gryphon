"""
Manual accounting script. Takes in an exchange and an exchange order id, queries the
exchange for details about the order, and adds the order and any associated trades to
the trading database just as if it were done by a running strategy.

TODOs:
- We should have a more graceful way of handling actors, probably that doesn't involve
  human users writing them in at the command line. Maybe we could work out a way for
  them to communicate the strategy they wish to account for and then this script can
  grab the actor from the actual file.
- Alternatively, a simple check would be 'has this actor ever been used in the database
  before? If not, then it might be an error and double check with the user.
- This script should be more thoroughly tested for non-BTC pairs.
"""

import termcolor as tc
import time

from delorean import epoch
import sqlalchemy

from gryphon.execution.strategies.base import Strategy
from gryphon.execution.lib.exchange_color import exchange_color
from gryphon.lib import session
from gryphon.lib.exchange.exceptions import *
from gryphon.lib.exchange.exchange_factory import *
from gryphon.lib.logger import get_logger
from gryphon.lib.models.order import Order
from gryphon.lib.money import Money

logger = get_logger(__name__)

EXPECTED_ACTORS = [
    'MANUAL',
    'MULTIEXCHANGE_LINEAR',
    'SIMPLE_ARB',
    'TRIVIAL_MM',
    'TRIVIAL_MM_EXT',
]

ACTOR_WARNING = """\
This strategy actor is not for any builtin strategy. Make sure that you have it right\
(include case) or your strategy's position and trades will not be accurate!\
"""


def manual_accounting(exchange_name, order_id, actor, execute=False):
    if actor not in EXPECTED_ACTORS:
        logger.warning(tc.colored(ACTOR_WARNING, color='yellow'))

    db = session.get_a_trading_db_mysql_session()

    try:
        exchange = make_exchange_from_key(exchange_name)
        exchange_data = make_exchange_data_from_key(exchange_name, db)

        vol_currency_key = '%s_total' % exchange.volume_currency.lower()

        try:
            exchange.cancel_order(order_id)
        except CancelOrderNotFoundError:
            pass

        details = exchange.get_order_details(order_id)

        unit_price = details['fiat_total'] / details[vol_currency_key].amount

        try:
            order = db.query(Order)\
                .filter(Order.exchange_order_id == order_id)\
                .filter(Order._exchange_name == exchange.name)\
                .one()

            order.time_created = epoch(details['time_created']).naive
            action = 'Updated'
        except sqlalchemy.orm.exc.NoResultFound:
            order = Order(
                actor,
                details['type'],
                details[vol_currency_key],
                unit_price,
                exchange,
                order_id,
            )

            order.time_created = epoch(details['time_created']).naive
            order.exchange_rate = Money('1', exchange.currency).to('USD').amount
            action = 'Added'

        position_change, position_change_no_fees = order.was_eaten(details)

        old_balance = exchange_data.balance[exchange.volume_currency]

        for currency_code, position in position_change.iteritems():
            exchange_data.position[currency_code] += position
            exchange_data.balance[currency_code] += position

        logger.info(
            'Order: %s for %.4f @ %.2f',
            order.order_type,
            order.volume,
            order.price,
        )

        for trade in order.trades:
            logger.info(
                'Trade: %s for %.4f @ %.2f',
                trade.trade_type,
                trade.volume,
                trade.price,
            )

        if execute:
            db.add(order)
            db.add(exchange_data)
            session.commit_mysql_session(db)

            logger.info(tc.colored(
                '%s order #%s and its %s trade(s)' % (
                action,
                order_id,
                len(details['trades'])),
                'green',
            ))

            logger.info(tc.colored(
                'Updated balance from %s to %s' % (old_balance,
                exchange_data.balance[exchange.volume_currency]),
                'green',
            ))

        else:
            logger.info(tc.colored(
                'pass --execute to save this order to the db',
                'red',
            ))

    finally:
        db.remove()

