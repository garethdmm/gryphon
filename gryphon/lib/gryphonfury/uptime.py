from datetime import timedelta

from gryphon.lib.models.trade import Trade
from gryphon.lib.models.order import Order
from gryphon.lib.money import Money

import sqlalchemy


"""
    Gives the portion of time that all exchanges in the given list were up
        in the given period.

    That is, the number of ten minute periods in the window in which every 
        one of these exchanges place an order.
"""
def global_uptime_for_exchanges_in_period(db, exchange_names, start_time, end_time):
    all_buckets = all_buckets_in_period(start_time, end_time)

    exchange_up_buckets = {}

    for exchange_name in exchange_names:
        exchange_up_buckets[exchange_name] = exchange_up_buckets_in_period(
            db,
            exchange_name,
            start_time,
            end_time,
        )  

    down_periods = 0.0

    for bucket in all_buckets:
        for exchange_name in exchange_names:
            if bucket not in exchange_up_buckets[exchange_name]:
                down_periods = down_periods + 1
                break

    downtime = down_periods / len(all_buckets)

    uptime = 1 - downtime

    return uptime


"""
    Gives a list of all the ten-minute periods in the given time range in
        which the given exchange placed orders.

    Similar to exchange_uptime_in_period except this gives you the actual
        list of times.
"""
def exchange_up_buckets_in_period(db, exchange_name, start_time, end_time):
    # this query gets a list of timestamps indicating the start of all
    # ten-minute periods in the given time window in which the exchange
    # bot placed at least one order
    up_buckets = db.query('time_period')\
        .from_statement("select from_unixtime(bucket) as time_period, count(*) as num_orders from (select unix_timestamp(`order`.time_created) - (unix_timestamp(`order`.time_created) % 600) as bucket from `order` where `order`.exchange_name = :exchange_name and `order`.time_created >= :start_time and `order`.time_created < :end_time) as buckets group by bucket")\
        .params(
            exchange_name=exchange_name,
            start_time=start_time,
            end_time=end_time,
        )\
        .all()

    up_buckets = [u[0] for u in up_buckets]

    return up_buckets


"""
    Gives the portion of time in the given period that the given exchange
        was up.

    An exchange is said to be "up" if it places at least one order in a 
        ten minute period.
"""
def exchange_uptime_in_period(db, exchange_name, start_time, end_time):
    num_periods = (end_time - start_time).total_seconds() / 600

    uptime = db.query('uptime')\
        .from_statement("select count(*)/:num_periods as uptime from (select from_unixtime(bucket) as time_period, count(*) as num_orders from (select unix_timestamp(`order`.time_created) - (unix_timestamp(`order`.time_created) % 600) as bucket from `order` where `order`.exchange_name = :exchange_name and `order`.time_created >= :start_time and `order`.time_created < :end_time) as buckets group by bucket) as up_buckets")\
        .params(
            num_periods=num_periods,
            exchange_name=exchange_name,
            start_time=start_time,
            end_time=end_time,
        )\
        .first()

    return uptime[0]


"""
    Helper function gives us a list of all the ten-minute periods between
        start_time and end_time.
"""
def all_buckets_in_period(start_time, end_time):
    num_periods = int((end_time - start_time).total_seconds() / 600)

    start_bucket = start_time - timedelta(minutes=start_time.minute % 10)

    all_buckets = [start_bucket + timedelta(minutes=10*i) for i in range(0,num_periods)]

    return all_buckets


