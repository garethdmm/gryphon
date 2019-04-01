from collections import defaultdict
import datetime
from decimal import Decimal

from delorean import Delorean
import sqlalchemy

from gryphon.lib.models.datum import Datum

def get_ticktime_series_for_exchange(db, exchange_name, start_time, end_time):
    exchange_name = exchange_name.upper()

    ticktime_series = []

    ticktimes = db\
        .query(Datum)\
        .filter_by(datum_type = '%s_TICK_TIME' % exchange_name)\
        .filter(Datum.time_created >= start_time)\
        .filter(Datum.time_created < end_time)\
        .all()

    if ticktimes:
        for tt in ticktimes:
            timestamp = Delorean(tt.time_created, "UTC").epoch * 1000
            datapoint = str(tt.numeric_value)

            ticktime_series.append([
                timestamp,
                datapoint,
            ])

    return ticktime_series


def get_mean_ticktime_from_series(ticktime_series):
    if len(ticktime_series) > 0:
        ticktimes = [Decimal(t[1]) for t in ticktime_series]

        return sum(ticktimes) / len(ticktimes)
    else:
        return 0


def get_tick_block_time_series_for_exchange(db, exchange_name, start_time, end_time):
    block_datum_type = exchange_name.upper() + '_TICK_BLOCK_TIME%'

    block_times = db.query(Datum)\
        .filter(Datum.time_created >= start_time)\
        .filter(Datum.time_created < end_time)\
        .filter(Datum.datum_type.like(block_datum_type))\
        .all()

    series = sort_blocks_into_series(block_times)

    return series


def get_block_name_from_datum_type(datum_type):
    return datum_type[datum_type.index('BLOCK_TIME_') + 11:]


def sort_blocks_into_series(block_times):
    block_series = defaultdict(lambda: [])

    for block_time in block_times:
        block_name = get_block_name_from_datum_type(block_time.datum_type)
        timestamp = Delorean(block_time.time_created, "UTC").epoch * 1000
        datapoint = str(block_time.numeric_value)

        block_series[block_name].append([
            timestamp,
            datapoint,
        ])

    return block_series
