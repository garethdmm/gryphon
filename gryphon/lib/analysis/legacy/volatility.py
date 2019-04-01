"""
This library gives two main interface functions right now:
  intraday_volatility_of_day ~ gives an indicator of how frothy trading within a day
    was. This measure is designed to be used to compare days to eachother.
  interday_volatility_of_period ~ gives an indicator of how frothy trading over a
    period of many days is. This could be used to compare months, or feel out what
    price swings in the "current regime" might be like.

Notes on volatility:

We have several different data sources we can calculate volatility of
  i) Our Core FV
  ii) Trade series
  iii) Middle prices from orderbooks

These functions use core fv to start because that is simplest, but we should move to
using the trade series or middle prices sometime soon. There are lots of different
choices for which type of volatility we look at: the period we look back, the sample
frequency, whether to annualize, whether to use returns or log returns, and which
metric to  use. Common metrics are stddev, variance, average absolute return.

Sources for this math:
- Section 3.2.4 of High Frequency Finance (textbook)
- Trading & Exchanges Chapter 20
- https://en.wikipedia.org/wiki/Volatility_(finance)
- http://www.investopedia.com/university/optionvolatility/volatility2.asp?no_header_alt=true
- http://quant.stackexchange.com/questions/2589/how-to-calculate-historical-intraday-volatility

TODO:
- Test methods against some known dataset.
- Move to looking at our saved trade history instead of core fv.
- Doublecheck that the way we annualize daily returns is valid.
"""

import datetime
import math

from cdecimal import Decimal
from delorean import Delorean
import numpy
from sqlalchemy import extract, func

from gryphon.lib.models.datum import Datum


def intraday_volatility_of_day(db, day_start):
    """
    Answers the question: "How volatile was this day". This is the standard deviation
    of hourly log return samples over a period of 24 hours beginning at day_start.

    Performance: very fast.
    """
    day_end = day_start + datetime.timedelta(days=1)

    volatility = hourly_volatility_in_period_from_core_fv_log_returns(
        db,
        day_start,
        day_end,
    )

    return volatility


def interday_volatility_of_period(db, first_day, last_day):
    """
    Answers the question "How bumpy was this period of several days?" The specific
    calculation is the standard deviation of daily log return samples at day end
    (11:59 pm UTC), annualized to a 365 day trading year. We can use this to calculate
    HV10/30/60/150 or arbitrary periods.

    Performance: don't try much more than 15 days at once.
    """

    period_end = last_day + datetime.timedelta(days=1)

    volatility = daily_volatility_in_period_from_core_fv_log_returns(
        db,
        first_day,
        period_end,
    )

    return volatility


def hourly_volatility_in_period_from_core_fv_log_returns(db, start_time, end_time):
    # get core_fv for each hour
    hourly_fv_series = get_hourly_core_fv_series_in_period(db, start_time, end_time)

    # convert to log returns
    log_returns_series = convert_to_log_returns(hourly_fv_series)

    # calculate volatility
    volatility = numpy.std(log_returns_series)

    return volatility


def one_hour_trailing_volatility_10m_buckets_core_fv_log_returns(db, end_time):
    """
    Answers the question "How bumpy was the last hour?"
    """
    # Round up end_time. Rounding up is preferable because this is an open/open
    # series, so rounding up gets us one more datapoint.
    end_time = round_datetime_up_to_10m(end_time)

    start_time = end_time - datetime.timedelta(seconds=3600)

    fv_series = get_ten_minute_core_fv_series_in_period(db, start_time, end_time)

    log_returns_series = convert_to_log_returns(fv_series)

    volatility = numpy.std(log_returns_series)

    return volatility


def three_hour_trailing_volatility_10m_buckets_core_fv_log_returns(db, end_time):
    """
    Answers the question "How bumpy was the last three hours?"
    """

    # Round up end_time. Rounding up is preferable because this is an open/open
    # series, so rounding up gets us one more datapoint.
    end_time = round_datetime_up_to_10m(end_time)

    start_time = end_time - datetime.timedelta(seconds=10800)

    fv_series = get_ten_minute_core_fv_series_in_period(db, start_time, end_time)

    log_returns_series = convert_to_log_returns(fv_series)

    volatility = numpy.std(log_returns_series)

    return volatility


def get_hourly_core_fv_series_in_period(db, start_time, end_time):
    """
    Get the hourly open-open price series in this period from our core fv datums.
    Like most of our periods, this one is inclusive on the left but not the right. So
    getting this series for a full day [Nov 1st, Nov 2nd) will give you 24 datapoints,
    but getting this series for a day and one minute will likely give you 25.
    """

    fundamental_value_series = []

    fv_series = db.query(
            Datum.time_created,
            Datum.numeric_value,
        )\
        .filter(Datum.time_created >= start_time)\
        .filter(Datum.time_created < end_time)\
        .filter(Datum.datum_type.like('%_CORE_FUNDAMENTAL_VALUE'))\
        .group_by(func.date(Datum.time_created), func.hour(Datum.time_created))\
        .all()

    # Do a teeny bit of sanity checking. The fanciness here is because timedelta
    # doesn't have a .hours method.
    delta = end_time - start_time
    hours = 24*delta.days + math.ceil(delta.seconds / 3600.0)
    assert(len(fv_series) == hours)

    fundamental_value_series = convert_datum_series_to_time_series(fv_series)

    return fundamental_value_series


def get_ten_minute_core_fv_series_in_period(db, start_time, end_time):
    """
    Get the ten-minute open-price series in this period from our core fv datums.
    Like most of our periods, this one is inclusive on the left but not the right. So
    getting this series for a full day [Nov 1st, Nov 2nd) will give you 24*6 == 144
    datapoints, but getting this series for a day and one minute will likely give you
    25.
    """

    fundamental_value_series = []

    fv_series = db.query(
            Datum.time_created,
            Datum.numeric_value,
        )\
        .filter(Datum.time_created >= start_time)\
        .filter(Datum.time_created < end_time)\
        .filter(Datum.datum_type.like('%_CORE_FUNDAMENTAL_VALUE'))\
        .group_by(
            func.date(Datum.time_created),
            func.hour(Datum.time_created),
            func.floor((func.minute(Datum.time_created) / 10))*10
        )\
        .all()

    # Do a teeny bit of sanity checking.
    delta = end_time - start_time
    ten_minutes = math.floor((delta.days*86400 + delta.seconds) / 600)
    assert(len(fv_series) == ten_minutes)

    fundamental_value_series = convert_datum_series_to_time_series(fv_series)

    return fundamental_value_series


def daily_volatility_in_period_from_core_fv_log_returns(db, start_time, end_time):
    # get core_fv for each hour
    daily_fv_series = get_daily_core_fv_series_in_period(db, start_time, end_time)

    # convert to log returns
    log_returns_series = convert_to_log_returns(daily_fv_series)

    # calculate volatility
    volatility = numpy.std(log_returns_series)

    # There's a question here of what "annualizing" a bitcoin price means. I decided
    # to use 365 as the constant, because that makes the intuition of the resulting
    # number "The standard deviation of the spread of log returns over a year". It
    # does mean that the number isn't comparable to stocks, which have a 252 day
    # trading year.
    annualized_volatility = volatility * math.sqrt(365)

    return annualized_volatility


def get_daily_core_fv_series_in_period(db, start_time, end_time):
    """
    Get the daily close-close price series in this period from our core fv datums.
    NOTE that we use close prices for this series, not open prices like for hourly.
    Getting this series for the period [Nov 1st, Nov 4th) will give you three
    datapoints.
    """

    fundamental_value_series = []

    # Getting the absolute last core_fv datum in a series of periods efficiently is
    # difficult, so this query gets the first datum in the last five minutes of
    # every day.
    fv_series = db.query(
            Datum.time_created,
            Datum.numeric_value,
        )\
        .filter(Datum.time_created >= start_time)\
        .filter(Datum.time_created < end_time)\
        .filter(func.hour(Datum.time_created) == 23)\
        .filter(func.minute(Datum.time_created) > 55)\
        .filter(Datum.datum_type.like('%_CORE_FUNDAMENTAL_VALUE'))\
        .group_by(func.date(Datum.time_created))\
        .all()

    # Do a teeny bit of sanity checking on the data
    delta = end_time - start_time
    assert(len(fv_series) == delta.days)

    fundamental_value_series = convert_datum_series_to_time_series(fv_series)

    return fundamental_value_series


### Helper functions ###


def convert_to_log_returns(series):
    """
    The logarithmic return between two periods is
    ln(p2 / p1) == ln(p2) - ln(p1)
    """

    # Note that Math.log defaults to the natural logarithm.
    log_price_series = [math.log(float(price)) for time, price in series]
    log_returns_series = numpy.diff([log_price for log_price in log_price_series])

    return log_returns_series


def convert_datum_series_to_time_series(datum_series):
    time_series = []

    for timestamp, value in datum_series:
        timestamp = Delorean(timestamp, "UTC").epoch * 1000

        time_series.append([
            timestamp,
            value,
        ])

    return time_series


def round_datetime_up_to_10m(dt):
    if dt.minute % 10 != 0:
        missing_minutes = 10 - dt.minute % 10
        return dt + datetime.timedelta(minutes=missing_minutes)
    else:
        return dt


# The below functions use ordinary returns [(p2 - p1)/p1] insted of log returns. Just
# including them here for reference and maybe we'll use them somewhere later.


def hourly_volatility_in_period_from_core_fv_ordinary_returns(db, start_time, end_time):
    # get core_fv for each hour
    hourly_fv_series = get_hourly_core_fv_series_in_period(db, start_time, end_time)

    # convert to returns
    returns_series = convert_to_ordinary_returns(hourly_fv_series)

    # calculate volatility
    volatility = numpy.std(returns_series)

    return volatility


def convert_to_ordinary_returns(series):
    price_series = [p[1] for p in series]

    returns_series = []

    for i in range(0, len(price_series) - 1):
        p2 = float(price_series[i+1])
        p1 = float(price_series[i])

        r = (p2 - p1) / p1

        returns_series.append(r)

    return returns_series


### Legacy Functions ###

def volatility(values, timestamps, window_time=10000):
    assert len(values) == len(timestamps)
    vols = []
    values.reverse()
    timestamps.reverse()
    for i in range(len(timestamps)):
        noted_timestamp = timestamps[i]
        relevant_values = []
        relevant_timestamps = []
        for j in range(len(timestamps)):
            index = j+i
            if index > len(timestamps)-1:
                break 
            elif noted_timestamp - timestamps[index] < window_time:
                relevant_values.append(values[index])
                relevant_timestamps.append(noted_timestamp - timestamps[index])
            else:
                break
        
        standard_deviation = np.std(relevant_values)
        mean = np.mean(relevant_values)
        #volatility = Decimal(standard_deviation)/Decimal(mean)
        vols.append(standard_deviation)
    vols.reverse()
    return vols


