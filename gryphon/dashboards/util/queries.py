from decimal import Decimal

from delorean import Delorean
import sqlalchemy
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from gryphon.lib.models.trade import Trade
from gryphon.lib.models.order import Order
from gryphon.lib.money import Money
from gryphon.dashboards.util.store_calculations import store_calculation_result


def get_all_trades_for_period(gryphon_session, start_time, end_time):
    trades = gryphon_session\
        .query(Trade)\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order').joinedload('datums'))\
        .all()

    return trades


def get_all_latest_order(gryphon_session, end_time):
    latest_order = gryphon_session\
        .query(Order)\
        .filter(Order.time_created < end_time)\
        .order_by(Order.time_created.desc())\
        .first()

    return latest_order


def get_manual_trades_for_period(gryphon_session, start_time, end_time):
    trades = gryphon_session\
        .query(Trade)\
        .join(Order)\
        .filter(Order.actor == 'Manual')\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order').joinedload('datums'))\
        .all()

    return trades


def get_manual_latest_order(gryphon_session, end_time):
    # this logic is weird but this is what was in the gryphon handler
    # we'll revisit it soon

    latest_order = gryphon_session\
        .query(Order)\
        .filter(Order._exchange_name == 'BITSTAMP')\
        .filter(Order.actor != "Manual")\
        .filter(Order.time_created < end_time)\
        .order_by(Order.time_created.desc())\
        .first()

    return latest_order


def get_strategy_trades_for_period(gryphon_session, strategy_name, start_time, end_time):
    trades = gryphon_session\
        .query(Trade)\
        .join(Order)\
        .filter(Order.actor == strategy_name)\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order').joinedload('datums'))\
        .all()

    return trades


def get_strategy_latest_order(gryphon_session, strategy_name, start_time, end_time):
    latest_order = gryphon_session\
        .query(Order)\
        .filter(Order.actor == strategy_name)\
        .filter(Order.time_created >= start_time)\
        .filter(Order.time_created < end_time)\
        .order_by(Order.time_created.desc())\
        .first()

    return latest_order


def get_multi_trades_for_period(gryphon_session, start_time, end_time):
    return get_strategy_trades_for_period(
        gryphon_session,
        'Multi',
        start_time,
        end_time,
    )


def get_multi_latest_order(gryphon_session, end_time):
    return get_strategy_latest_order_for_period(
        gryphon_session,
        'Multi',
        start_time,
        end_time,
    )


def get_exchange_trades_for_period(gryphon_session, exchange, start_time, end_time):
    trades = gryphon_session\
        .query(Trade)\
        .join(Order)\
        .filter(Order._exchange_name == exchange)\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order').joinedload('datums'))\
        .all()

    return trades


def get_exchange_latest_order(gryphon_session, exchange_name, end_time):
    # Exclude Manual trades since they don't have a fundamental value
    latest_order = gryphon_session\
        .query(Order)\
        .filter(Order._exchange_name == exchange_name)\
        .filter(Order.actor != "Manual")\
        .filter(Order.time_created < end_time)\
        .order_by(Order.time_created.desc())\
        .first()

    return latest_order


def get_total_volume_in_period(db, start_time, end_time):
    total_volume = db\
        .query(func.sum(Trade._volume))\
        .filter(Trade.time_created >= start_time)\
        .filter(Trade.time_created < end_time)\
        .first()

    return total_volume[0]


def get_total_volume_for_exchange_in_period_from_database(db, start_time, end_time, exchange):
    results = db.query('sum(trade.volume)')\
        .from_statement("select sum(trade.volume) from `order` inner join trade on `order`.order_id=trade.order_id where `order`.time_created < :end_time and `order`.time_created > :start_time and `order`.exchange_name = :exchange")\
        .params(
            start_time=start_time, 
            end_time=end_time, 
            exchange=exchange)\
        .first()

    total_volume = results[0]

    if not total_volume:
        total_volume = Decimal(0)

    return total_volume


def get_last_trade_price_in_usd(db):
    last_trade = db.query(Trade)\
        .order_by(Trade.time_created.desc())\
        .first()

    last_trade_price = last_trade.order.price.to(
        'USD',
        exchange_rate_to_usd=last_trade.order.exchange_rate,
    )

    return last_trade_price


def get_last_fundamental_value_in_usd(db):
    last_order = db.query(Order)\
        .order_by(Order.time_created.desc())\
        .first()

    fundamental_value = last_order.fundamental_value.to(
        'USD',
        exchange_rate_to_usd=last_order.exchange_rate,
    )

    return fundamental_value


def get_open_bids_and_asks(db):
    quotes = db.query(Order)\
        .filter(Order.status == 'OPEN')\
        .filter(Order.time_created > Delorean().last_hour(1).naive())\
        .filter(Order.actor == 'MULTI')\
        .all()

    bids = [q for q in quotes if q.order_type == Order.BID]
    asks = [q for q in quotes if q.order_type == Order.ASK]

    bids = sorted(
        bids, 
        key=lambda quote: quote.price.amount*quote.exchange_rate,
        reverse=True,
    )

    asks = sorted(
        asks, 
        key=lambda quote: quote.price.amount*quote.exchange_rate,
        reverse=True,
    )

    quotes = {
        'bids': bids,
        'asks': asks,
    }

    return quotes


def get_num_active_exchanges_in_period_from_database(db, start_time, end_time):
    column_name = 'num_live_exchanges'

    results = db.query(column_name)\
        .from_statement("select count(distinct `order`.exchange_name) as :column_name from `order` where `order`.time_created > :start_time and `order`.time_created < :end_time")\
        .params(
            column_name=column_name,
            start_time=start_time, 
            end_time=end_time)\
        .first()

    return results[0]

def strip_datetime_for_db_operations(dt):
    """
    Some of our queries get very slow unless we remove the timezone info
    before we put them into sql.
    """
    return dt.replace(tzinfo=None)

