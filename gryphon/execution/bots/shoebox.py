import os
import random
import subprocess
import time

from delorean import Delorean
import pygerduty
from sqlalchemy.orm import joinedload

from gryphon.execution.lib.heartbeat import heartbeat
from gryphon.lib import hackernewsie
from gryphon.lib import redditor
from gryphon.lib import session
from gryphon.lib.exchange import exchange_factory
import gryphon.lib.gryphonfury.positions as positions
import gryphon.lib.gryphonfury.revenue as revenue_lib
from gryphon.lib.logger import get_logger
from gryphon.lib.models.datum import DatumRecorder
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money
from gryphon.lib.slacker import Slacker
from gryphon.lib.time_parsing import parse
from gryphon.lib.util.time import humanize_seconds

logger = get_logger(__name__)

TICK_SLEEP = 60
SHOEBOX_HEARTBEAT_KEY = 'SHOEBOX'


def run():
    db = session.get_a_trading_db_mysql_session()

    DatumRecorder().create(db=db)

    logger.info('Reporting for duty.')

    try:
        while True:
            current_time = Delorean().datetime

            try:
                update_tx_hashes(db)
            except Exception as e:
                logger.exception('Error while updating transaction hashes')

            # Checking the exact minute amounts works because the shoebox is ticking every 1m
            # This may not work 100% if the shoebox tick takes any noticable amount of time
            # to run. In that case we might tick at the end of xx:59 and the beginning of xx:01,
            # and these tasks wouldn't run. We'll keep an eye on it and may have to add some
            # persistance later.

            # every 5 minutes
            if current_time.minute % 5 == 0:
                try:
                    get_breaking_bitcoin_news()
                except Exception:
                    logger.exception('Error while getting breaking news')

            # every hour
            if current_time.minute == 0:
                money_moving()
                manual_btc_withdrawals(db)

            # end of day UTC
            if current_time.hour == 0 and current_time.minute == 0:
                notify_revenue(db)

            heartbeat(SHOEBOX_HEARTBEAT_KEY)

            session.commit_mysql_session(db)
            logger.info('Going to sleep for %s.' % humanize_seconds(TICK_SLEEP))
            time.sleep(TICK_SLEEP)
    finally:
        db.remove()


def get_breaking_bitcoin_news():
    reddit_breaking_news = redditor.get_reddit_breaking_news('bitcoin', upvote_threshold=500)

    hn_keyword_dict = {
        'bitcoin': 15,
        'bitstamp': 5,
        'bitfinex': 5,
        'cavirtex': 5,
        'quadriga': 5,
        'okcoin': 5,
        'coinbase': 5,
        'coinsetter': 5,
        'gemini': 5,
        'kraken': 5,
    }

    hn_breaking_news = hackernewsie.get_hn_breaking_news(hn_keyword_dict)

    for news in reddit_breaking_news:
        news['source'] = 'Reddit'

    for news in hn_breaking_news:
        news['source'] = 'HN'

    breaking_news = reddit_breaking_news + hn_breaking_news
    if breaking_news:
        message = 'Breaking News:\n'

        for news in breaking_news:
            message += '<%s|%s> (<%s|%s comments>)\n\n' % (news['url'], news['title'], news['comments_url'], news['source'])

        slacker = Slacker('#news', 'news')
        slacker.notify(message)


def update_tx_hashes(db):
    logger.info('Updating transaction hashes.')
    txs = in_progress_transactions(db)
    for tx in txs:
        tx.update_tx_hash()


def in_progress_transactions(db):
    txs = db.query(Transaction)\
        .filter_by(transaction_status='IN_TRANSIT')\
        .join(ExchangeData)\
        .order_by(Transaction.time_created)\
        .all()
    return txs


def load_devs():
    devs = [
        {
            'name': 'gareth',
            'starts_work': 11,
            'ends_work': 19,
            'timezone': 'US/Pacific',
        },
        {
            'name': 'trevor',
            'starts_work': 11,
            'ends_work': 19,
            'timezone': 'US/Pacific',
        },
        {
            'name': 'ross',
            'starts_work': 11,
            'ends_work': 19,
            'timezone': 'US/Pacific',
        },
    ]

    return devs


def dev_checkins():
    """Sends a checkin message to all the working devs at the top of the hour"""

    logger.info('Running dev checkins')

    # devs should get pinged after every hour of work
    # so if they are working from 10am to 5pm they should get pinged
    # at 11am, 12pm, 1pm, 2pm, 3pm, 4pm and 5pm
    devs = load_devs()

    for dev in devs:
        current_time = Delorean(timezone=dev['timezone'])

        if is_working(current_time, dev):
            message_dev_for_checkin(dev, current_time)


def dev_summaries():
    """Sends a summary request message to all the working devs at the end of each workday"""
    logger.info('Running dev summaries')

    # devs should get pinged after every hour of work
    # so if they are working from 10am to 5pm they should get pinged
    # at 11am, 12pm, 1pm, 2pm, 3pm, 4pm and 5pm
    devs = load_devs()

    for dev in devs:
        current_time = Delorean(timezone=dev['timezone'])

        if is_end_of_workday(current_time, dev):
            message_dev_for_summary(dev)


def is_end_of_workday(current_time, dev):
    current_hour = current_time.datetime.hour
    is_end_of_day = (current_hour == dev['ends_work'])
    return is_workday(current_time) and is_end_of_day


def is_workday(current_time):
    weekday = current_time.datetime.weekday()
    is_saturday = (weekday == 5)
    is_sunday = (weekday == 6)

    return (not is_saturday and not is_sunday)


def is_working(current_time, dev):
    """Is the dev working at the current time?"""

    current_hour = current_time.datetime.hour
    is_working_hours = (current_hour > dev['starts_work'] and current_hour <= dev['ends_work'])
    return is_workday(current_time) and is_working_hours


def message_dev_for_summary(dev):
    channel = '#general'
    message = 'Hey @%s, what did you get up to today?' % dev['name']
    emoji = fun_emoji()
    bot_name = fun_bot_name(emoji)
    slacker = Slacker(channel, bot_name, icon_emoji=emoji)
    slacker.notify(message)


def message_dev_for_checkin(dev, current_time):
    logger.info('pinging @%s' % dev['name'])

    channel = '@%s' % dev['name']
    message = 'Time for a quick checkin'
    emoji = clock_emoji(current_time)
    slacker = Slacker(channel, 'checkin', icon_emoji=emoji)
    slacker.notify(message)


def clock_emoji(time):
    hour = time.datetime.hour
    # 14 -> 2(pm)
    clock_hour = hour % 12

    # there's no 0-hour emoji
    if clock_hour == 0:
        clock_hour = 12

    return ':clock%s:' % clock_hour


def fun_emoji():
    fun_emoji_list = [
        ':snowman:',
        ':cat:',
        ':dog:',
        ':mouse:',
        ':hamster:',
        ':rabbit:',
        ':wolf:',
        ':frog:',
        ':tiger:',
        ':koala:',
        ':bear:',
        ':pig:',
        ':cow:',
        ':boar:',
        ':monkey:',
        ':horse:',
        ':snake:',
        ':bird:',
        ':baby_chick:',
        ':chicken:',
        ':penguin:',
        ':turtle:',
        ':bug:',
        ':honeybee:',
        ':ant:',
        ':beetle:',
        ':snail:',
        ':octopus:',
        ':tropical_fish:',
        ':fish:',
        ':whale:',
        ':whale2:',
        ':dolphin:',
        ':rat:',
        ':octocat:',
        ':squirrel:',
        ':ghost:',
    ]
    return random.choice(fun_emoji_list)


def fun_bot_name(emoji):
    # ':tropical_fish:' -> 'Tropical Fishbot'
    return ' '.join([w.capitalize() for w in emoji.replace(':', '').split('_')]) + 'bot'

MANUAL_BTC_EXCHANGES = {
    'CAVIRTEX': Money('40', 'BTC'),
    'COINSETTER': Money('40', 'BTC'),
}
BTC_TRANSFER_UNIT = Money('30', 'BTC')


def manual_btc_withdrawals(db):
    """
    Check the Manual BTC exchanges for being above their target. Ping a dev on hipchat if they are.
    """

    logger.info('Running manual BTC withdrawals')

    for name, target in MANUAL_BTC_EXCHANGES.iteritems():
        exchange_db = exchange_factory.make_exchange_data_from_key(name, db)
        if exchange_db.balance['BTC'] > target:
            withdrawal_amount = exchange_db.balance['BTC'] - target
            if withdrawal_amount > BTC_TRANSFER_UNIT:
                btc_withdrawal_notification(exchange_db, withdrawal_amount)


def btc_withdrawal_notification(exchange_db, amount):
    on_call_dev = get_on_call_dev()
    amount = amount.round_to_decimal_places(0)
    channel = '@%s' % on_call_dev
    message = 'Do a %d BTC withdrawal from %s' % (amount.amount, exchange_db.name)

    logger.info('Hipchat ping: %s' % message)

    slacker = Slacker(channel, 'withdrawals', icon_emoji=':moneybag:')
    slacker.notify(message)


def money_moving():
    current_time = Delorean().datetime

    morning_timeslot = parse('9am -0800').datetime  # when we get up in PST
    afternoon_timeslot = parse('3:30pm -0500').datetime  # 4pm EST is BMO's wire cutoff

    in_morning_timeslot = (current_time.hour == morning_timeslot.hour and
        current_time.minute == morning_timeslot.minute)

    in_afternoon_timeslot = (current_time.hour == afternoon_timeslot.hour and
        current_time.minute == afternoon_timeslot.minute)

    if in_morning_timeslot or in_afternoon_timeslot:
        on_call_dev = get_on_call_dev()
        channel = '@%s' % on_call_dev

        if in_morning_timeslot:
            message = 'Time for early morning money moving!'
        elif in_afternoon_timeslot:
            message = 'Time for afternoon money moving! (Wire cutoff is 4pm EST)'

        slacker = Slacker(channel, 'mover', icon_emoji=':moneybag:')
        slacker.notify(message)


def notify_revenue(db):
    # beginning of last UTC day
    start_time = Delorean().last_day().truncate('day').datetime
    end_time = Delorean().truncate('day').datetime

    # This revenue calculating logic takes about 10s to run
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
        .filter(Trade.time_created < end_time)\
        .options(joinedload('order'))\
        .order_by(Trade.time_created)\
        .all()

    matched_trades, _ = revenue_lib.split_trades(
        open_position_trades + trades,
    )

    __, revenue, __, __ = revenue_lib.profit_data(matched_trades, 'USD')

    slacker = Slacker('#general', 'revenue', icon_emoji=':moneybag:')
    slacker.notify('We made %s today' % revenue)


def get_on_call_dev():
    """ Returns the username (gareth, ross, trevor) of the current on-call dev """
    pager = pygerduty.PagerDuty('tinker', os.environ['PAGERDUTY_API_KEY'])

    escalation_policies = pager.escalation_policies.on_call()
    default_policy = [p for p in escalation_policies if p.name == 'Default'][0]

    on_call_users = default_policy.on_call
    on_call = [u for u in on_call_users if u.level == 1][0]

    name = on_call.user.name
    first_name = name.split()[0]
    username = first_name.lower()

    return username
