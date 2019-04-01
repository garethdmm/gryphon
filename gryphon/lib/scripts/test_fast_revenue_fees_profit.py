"""
Test script for the new fast revenue function. Runs both revenue functions on a
random period and checks their results are the same.
"""

import pyximport; pyximport.install()

from cdecimal import *
from datetime import datetime, timedelta
import os
import random

from delorean import Delorean

import gryphon.lib.gryphonfury.profit as gryphon_profit
from gryphon.lib import session


def get_random_period():
    """
    Get a random period of between 0 and 24 hours between February and October of
    2015.
    """
    start = datetime(
        2015,
        random.randint(2, 10),
        random.randint(1,30),
        random.randint(0,23),
    )

    end = start + timedelta(hours=random.randint(0, 20))

    return start, end


def test_fast_revenue():
    db = session.get_a_trading_db_mysql_session()

    for i in range(1, 30):
        start, end = get_random_period()

        print '%s, %s' % (start, end)

        slow_revenue = gryphon_profit.revenue_in_period(db, start, end)
        fast_revenue = gryphon_profit.fast_revenue_in_period(db, start, end)

        # These numbers will be off by tiny fractions due to rounding differences
        # between python and sql. Four decimal places of precision here (1/100th of
        # a cent, is good enough.
        result = (slow_revenue.round_to_decimal_places(4)
                      == fast_revenue.round_to_decimal_places(4))

        if not result:
            print 'BAD: %s, != %s' % (slow_revenue, fast_revenue)
        else:
            print 'GOOD: %s, == %s' % (slow_revenue, fast_revenue)

    db.remove()


def test_fast_profit():
    db = session.get_a_trading_db_mysql_session()

    for i in range(1, 30):
        start, end = get_random_period()

        print '%s, %s' % (start, end)

        slow_profit = gryphon_profit.profit_in_period(db, start, end)
        fast_profit = gryphon_profit.fast_profit_in_period(db, start, end)

        result = (slow_profit.round_to_decimal_places(4)
                      == fast_profit.round_to_decimal_places(4))

        if not result:
            print 'BAD: %s, != %s' % (slow_profit, fast_profit)
        else:
            print 'GOOD: %s, == %s' % (slow_profit, fast_profit)

    db.remove()


def test_fast_revenue_fees_profit():
    db = session.get_a_trading_db_mysql_session()

    for i in range(1, 30):
        start, end = get_random_period()

        print '%s, %s' % (start, end)

        slow_revenue, slow_fees, slow_profit = gryphon_profit.revenue_fees_profit_in_period(db, start, end)
        fast_revenue, fast_fees, fast_profit = gryphon_profit.fast_revenue_fees_profit_in_period(db, start, end)

        result = (slow_revenue.round_to_decimal_places(4)
                      == fast_revenue.round_to_decimal_places(4) and
                      slow_profit.round_to_decimal_places(4)
                      == fast_profit.round_to_decimal_places(4) and
                      slow_fees.round_to_decimal_places(4)
                      == fast_fees.round_to_decimal_places(4))

        if not result:
            print 'BAD'
        else:
            print 'GOOD'

    db.remove()

test_fast_revenue()
