from tinkerpy.models.trade import Trade
from tinkerpy.models.order import Order

import sqlalchemy
from sqlalchemy.orm import joinedload

from delorean import Delorean
from decimal import Decimal


""" 
    Old versions that were used up until about November 2014 when multi
    became our main algorithm. We may still want these in the future so
    I'm leaving them in a new file.
"""

def old_get_multi_trades_for_period(self, start_time, end_time):
    # this gets the union of all multi trades and cavirtex/multi trades

    # cavirtex/vault trades that are not multi trades
    multi_trades = self.trading_db.query(Trade)\
        .join(Order)\
        .filter(Order._exchange_name.in_((
            "CAVIRTEX", 
            "VAULTOFSATOSHI"))
        )\
        .filter(~Order.actor.in_(["Manual", "Multi", "runner[nightly_position_close]"]))\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order'))\
        .all()

    # all multi trades
    multi_trades += self.trading_db.query(Trade)\
        .join(Order)\
        .filter(Order.actor == "Multi")\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order'))\
        .all()

    return multi_trades


def old_get_linear_trades_for_period(self, start_time, end_time):
    exchanges = ['BITSTAMP', 'BITFINEX', 'KRAKEN', 'ITBIT']

    trades = self.trading_db.query(Trade)\
        .join(Order)\
        .filter(Order._exchange_name.in_(exchanges))\
        .filter(~Order.actor.in_(["Manual", "Multi", "runner[nightly_position_close]"]))\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order'))\
        .all()

    return trades


