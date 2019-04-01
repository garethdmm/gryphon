import time
import subprocess
import termcolor as tc

from delorean import Delorean
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from gryphon.execution.lib.heartbeat import heartbeat
from gryphon.lib import assets
from gryphon.lib import session
from gryphon.lib.exchange.exchange_factory import ALL_EXCHANGE_KEYS
import gryphon.lib.gryphonfury.positions as positions
import gryphon.lib.gryphonfury.revenue as revenue_lib
from gryphon.lib.logger import get_logger
from gryphon.lib.models.datum import Datum
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.money import Money

logger = get_logger(__name__)


DAILY_PROFIT_THRESHOLD = Money.loads('USD -500')
OPEN_PL_THRESHOLD = Money.loads('USD -200')
TICK_SLEEP = 30
FV_MOVEMENT_MINIMUM = 0.10
LARGE_EXCHANGES = [
    'bitfinex',
    'bitstamp',
    'coinbase',
    'itbit',
    'kraken',
    'okcoin'
]
INTER_EXCHANGE_SPREAD_THRESHOLD = 5
PREDICTIVE_VOLUME_REDIS_KEY = 'ML_PREDICTION'

OVERWATCH_HEARTBEAT_KEY = 'OVERWATCH_%s'


def watch():
    db = session.get_a_trading_db_mysql_session()
    r = session.get_a_redis_connection()

    logger.info('Reporting for duty.')

    try:
        while True:
            logger.info('Scanning for abnormalities.')

            check_profit(db)
            check_open_pl(db)
            check_ticktimes(db)
            check_position(db)
            check_btc_net_assets(db)
            check_spreads_are_normal(db)
            check_fv_not_stagnant(db)
            check_fv_predictor_key_set(r)

            # for some reason this commit is needed to pick up changes on
            # subsequent queries.
            session.commit_mysql_session(db)

            logger.info('Going to sleep for %s seconds.' % TICK_SLEEP)
            time.sleep(TICK_SLEEP)
    finally:
        db.remove()


def check_profit(db):
    # beginning of current UTC day
    start_time = Delorean().truncate('day').datetime

    # This profit calculating logic takes about 10s to run
    open_position_offset = positions.fast_position(
        db,
        end_time=start_time,
    )

    open_position_trades = revenue_lib.open_position_trades(
        open_position_offset,
        db,
        start_time,
    )

    trades = db\
        .query(Trade)\
        .join(Order)\
        .filter(Order.actor == 'Multi')\
        .filter(Trade.time_created >= start_time)\
        .options(joinedload('order'))\
        .order_by(Trade.time_created)\
        .all()

    matched_trades, _ = revenue_lib.split_trades(
        open_position_trades + trades,
    )

    daily_pl = revenue_lib.realized_pl(matched_trades, 'USD')

    logger.info('Daily Profit to date: %s' % daily_pl)

    if daily_pl > DAILY_PROFIT_THRESHOLD:
        succeed('PROFIT')
    else:
        fail('PROFIT')


def check_open_pl(db):
    # beginning of current UTC day
    start_time = Delorean().datetime

    # This profit calculating logic takes about 10s to run
    open_position_offset = positions.fast_position(
        db,
        end_time=start_time,
    )

    open_position_trades = revenue_lib.open_position_trades(
        open_position_offset,
        db,
        start_time,
    )

    latest_order = db\
        .query(Order)\
        .order_by(Order.time_created.desc())\
        .filter(Order.actor == 'Multi')\
        .filter(Order._fundamental_value != None)\
        .first()

    open_pl = revenue_lib.open_pl(
        open_position_trades,
        latest_order.fundamental_value.to('USD'),
        'USD',
    )

    logger.info('Open PL: %s' % open_pl)

    if open_pl > OPEN_PL_THRESHOLD:
        succeed('OPEN_PL')
    else:
        fail('OPEN_PL')


# Stop heartbeating if there are any ticktimes longer than a minute in the
# last five minutes.
def check_ticktimes(db):
    five_minutes_ago = Delorean().truncate('minute').last_minute(5).naive

    longest_tick = db\
        .query(Datum)\
        .filter(Datum.time_created >= five_minutes_ago)\
        .filter(Datum.datum_type.like('%TICK_TIME%'))\
        .order_by(Datum.numeric_value.desc())\
        .first()

    if longest_tick:
        logger.info('Longest recent tick: %s' % longest_tick.numeric_value)

        if longest_tick.numeric_value < 60:
            succeed('TICKTIME')
        else:
            fail('TICKTIME')
    else:
        fail('TICKTIME', 'No recent tick data')


def check_position(db):
    cached_position = positions.cached_multi_position(db)
    multi_position = positions.fast_position(db)

    if multi_position == cached_position:
        succeed('POSITION')
    else:
        detail = 'Cached: %s != DB: %s' % (cached_position, multi_position)
        fail('POSITION', detail)


def check_btc_net_assets(db):
    btc_net_assets_error = assets.calculate_btc_net_assets_error(db)

    if btc_net_assets_error == Money(0, 'BTC'):
        succeed('BTC_NET_ASSETS')
    else:
        detail = 'Error: %s' % btc_net_assets_error
        fail('BTC_NET_ASSETS', detail)


def check_spreads_are_normal(db):
    """
    Check whether any exchange has diverged by more than $10 from core fv in the
    last five minutes.
    """

    current_core_fv_datum = db\
        .query(Datum)\
        .filter(Datum.datum_type.like('%CORE_FUNDAMENTAL_VALUE'))\
        .order_by(Datum.time_created.desc())\
        .first()

    current_core_fv = current_core_fv_datum.numeric_value
    last_five = Delorean().last_minute(5).naive
    native_fvs = {}

    for exchange_name in ALL_EXCHANGE_KEYS:
        datum_name = '%s_NATIVE_FUNDAMENTAL_VALUE' % exchange_name.upper()

        if exchange_name in LARGE_EXCHANGES:
            exchange_native_fv = db\
                .query(Datum)\
                .filter(Datum.datum_type == datum_name)\
                .filter(Datum.time_created > last_five)\
                .order_by(Datum.time_created.desc())\
                .first()

            if exchange_native_fv:
                native_fvs[exchange_name] = exchange_native_fv.numeric_value

    sanity = True

    for exchange_name, fv in native_fvs.iteritems():
        if abs(fv - current_core_fv) > INTER_EXCHANGE_SPREAD_THRESHOLD:
            sanity = False
            break

    if sanity:
        succeed('SPREADS')
    else:
        fail('SPREADS')


def check_fv_not_stagnant(db):
    """
    Check that each large exchange's fundamental value is moving normally, catching
    the bug where coinbase had the same FV for hours on end a few weeks ago (18 Oct
    2015).

    We raise an alarm if the fundamental value hasn't moved by more than ten cents in
    the last period. For large exchanges this period is 30 minutes and  for small
    exchanges this period is an hour.
    """

    last_thirty = Delorean().last_minute(30).naive
    sanity = True

    for exchange_name in ALL_EXCHANGE_KEYS:
        datum_name = '%s_NATIVE_FUNDAMENTAL_VALUE' % exchange_name.upper()

        if exchange_name in LARGE_EXCHANGES:
            datums = db\
                .query(
                    func.max(Datum.numeric_value),
                    func.min(Datum.numeric_value),
                )\
                .filter(Datum.datum_type == datum_name)\
                .filter(Datum.time_created > last_thirty)\
                .first()

            max_fv = datums[0]
            min_fv = datums[1]

            if max_fv is None or min_fv is None:
                # Currently have a bug whereby native fv's are not being recorded all the
                # time, this is a hack around that for now.
                continue

            if max_fv - min_fv < FV_MOVEMENT_MINIMUM:
                logger.info(exchange_name + ' fundamental value not moving as expected!')
                sanity = False
                break

    if sanity:
        succeed('FV_MOTION')
    else:
        fail('FV_MOTION')


def check_fv_predictor_key_set(r):
    val = r.get(PREDICTIVE_VOLUME_REDIS_KEY)

    if val is not None and (int(val) == 1 or int(val) == 0):
        succeed('FV_PREDICTOR_KEY')
    else:
        fail('FV_PREDICTOR_KEY')


def succeed(check_id):
    heartbeat(OVERWATCH_HEARTBEAT_KEY % check_id)
    message = '%s passed' % check_id
    logger.info(tc.colored(message, 'green'))


def fail(check_id, detail_msg=None):
    message = '%s failed' % check_id

    if detail_msg:
        message += ': %s' % detail_msg

    logger.error(tc.colored(message, 'red'))

