import csv
from datetime import timedelta
import gzip
import StringIO

from delorean import epoch
import requests
from sqlalchemy.sql import func

from gryphon.lib import session
from gryphon.lib.bitcoinwisdom import BitcoinWisdom
from gryphon.lib.exchange_volume_lib import get_single_exchange_volume_on_day_from_db_tickers
from gryphon.lib.models.emeraldhavoc.trade import Trade
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse


historical_data_url = 'http://api.bitcoincharts.com/v1/csv/%s%s.csv.gz'

historically_available_exchanges = [
    ['BITSTAMP', 'bitstamp', 'USD', 'BTC'],
    ['BITFINEX', 'bitfinex', 'USD', 'BTC'],
    ['COINBASE', 'coinbase', 'USD', 'BTC'],
    ['COINBASE_CAD', 'coinbase', 'CAD', 'BTC'],
    ['ITBIT', 'itbit', 'USD', 'BTC'],
    ['KRAKEN', 'kraken', 'EUR', 'BTC'],
]

all_exchanges = [
    'BITSTAMP',
    'BITFINEX',
    'KRAKEN',
    'COINBASE',
    'COINBASE_CAD',
    'ITBIT',
    'CAVIRTEX',
    'QUADRIGA',
    #'COINSETTER',
]

bw_exchanges = [
    'BITSTAMP',
    'BITFINEX',
    'KRAKEN',
]

test_start_date = parse('2015-12-1').datetime
test_end_date = parse('2015-12-15').datetime

def backfill_trades(exchanges):
    for e in exchanges:
        trades = get_trades_to_backfill(e[0], e[1], e[2], e[3])
        write_trades_to_db(e[0], trades)


def get_trades_to_backfill(our_exchange_id, exchange, price_currency, volume_currency):
    our_trades = get_our_recorded_trades(our_exchange_id.upper())
    oldest_trade_timestamp = our_trades[0][0]
    historical_trades = get_historical_trades(exchange.lower(), price_currency, volume_currency)
    trades_to_add = [t for t in historical_trades if t[0] < oldest_trade_timestamp]

    # sort the trades to add in adding the most recent one first.
    sorted_trades = sorted(trades_to_add, key=lambda k: k[0], reverse=True)

    return sorted_trades


def write_trades_to_db(our_exchange_id, trades_list):
    db = session.get_a_gds_db_mysql_session()
    try:
        for i in range(len(trades_list)):
            trade = Trade(
                trades_list[i][1],
                trades_list[i][2],
                our_exchange_id,
                trades_list[i][0],
                None,
                source='BITCOINCHARTS'
            )
            db.add(trade)
            if i % 30 == 0:
                session.commit_mysql_session(db)

        session.commit_mysql_session(db)

    finally:
        db.remove()


def get_historical_trades(exchange, price_currency, volume_currency='BTC'):
    r = requests.get(historical_data_url % (exchange, price_currency))
    compressedFile = StringIO.StringIO()
    compressedFile.write(r.content)
    compressedFile.seek(0)
    decompressedFile = gzip.GzipFile(fileobj=compressedFile, mode='rb')

    try:
        reader = csv.reader(decompressedFile)
        trades = []
        for row in reader:
            timestamp = epoch(int(row[0])).datetime.replace(tzinfo=None)
            price = Money(row[1], price_currency)
            volume = Money(row[2], volume_currency)
            trades.append([timestamp, price, volume])

        return trades

    finally:
        decompressedFile.close()


def get_our_recorded_trades(exchange):
    db = session.get_a_gds_db_mysql_session()
    try:
        trades_for_ex = db.query(Trade).\
            filter_by(exchange=exchange.upper()).\
            order_by(Trade.exchange_trade_id).all()
        norm_trades = [[t.timestamp.replace(tzinfo=None), t.price, t.volume] for t in trades_for_ex]

        return norm_trades

    finally:
        db.remove()


def get_our_recorded_exchange_trade_volume_for_period(exchange, start_date, end_date):
    db = session.get_a_gds_db_mysql_session()
    try:
        exchange_volume = db.query(func.sum(Trade._volume).label('exchange_volume'))\
            .filter_by(exchange=exchange.upper())\
            .filter(Trade.timestamp >= start_date)\
            .filter(Trade.timestamp < end_date).first()
        return Money(exchange_volume[0], 'BTC')

    finally:
        db.remove()


def get_our_recorded_ticker_volume_for_period(exchange, start_date, end_date):
    db = session.get_a_gds_db_mysql_session()
    try:

        d = start_date
        volume = Money(0, 'BTC')
        while d < end_date:
            volume += get_single_exchange_volume_on_day_from_db_tickers(
                db,
                exchange,
                start_date,
            )
            d += timedelta(days=1)

        return volume

    finally:
        db.remove()


# auditing functions

def audit_ticker_volume_individual_days(exchange_list, start_date=test_start_date, end_date=test_end_date):
    d = start_date
    while d < test_end_date:
        print '\n\nAuditing: %s' % d
        day_after = d + timedelta(days=1)
        audit_all_ticker_volume(exchange_list, d, day_after)
        d = day_after

def audit_all_ticker_volume(exchange_list, start_date=test_start_date, end_date=test_end_date):
    for exchange in exchange_list:
        audit_ticker_volume(exchange, start_date, end_date)


def audit_all_bw_volume(exchange_list):
    start_date = parse('2015-12-01').datetime
    end_date = parse('2015-12-15').datetime
    for exchange in exchange_list:
        audit_bw_volume(exchange, start_date, end_date)


def audit_ticker_volume(exchange, start_date, end_date):
    ticker_volume = get_our_recorded_ticker_volume_for_period(
        exchange,
        start_date,
        end_date,
    )

    our_volume = get_our_recorded_exchange_trade_volume_for_period(
        exchange,
        start_date,
        end_date,
    )

    print '%s  Our Volume:%s  Ticker Volume:%s, Accuracy: %s' % (
        exchange,
        our_volume,
        ticker_volume,
        our_volume / ticker_volume,
    )


def audit_bw_volume(exchange, start_date, end_date):
    bw_exchange = BitcoinWisdom(exchange=exchange)
    bw_volume = bw_exchange.volume_in_period(start_date, end_date)

    our_volume = get_our_recorded_exchange_trade_volume_for_period(exchange, start_date, end_date)
    print '%s  Our Volume:%s  BW Volume:%s, Accuracy: %s' % (exchange, our_volume, bw_volume, our_volume / bw_volume)


def compare_all_exchanges():
    for ex in historically_available_exchanges:
        compare_ours_to_history(ex[0], ex[1], ex[2], ex[3])


def compare_ours_to_history(our_exchange_id, exchange, price_currency, volume_currency='BTC'):
    hist_trades = get_historical_trades(
        exchange.lower(),
        price_currency, volume_currency,
    )
    our_trades = get_our_recorded_trades(our_exchange_id.upper())

    start = parse('2015-11-27 0:0:0').datetime.replace(tzinfo=None)
    end = parse('2015-11-27 11:59:59').datetime.replace(tzinfo=None)

    print our_exchange_id.upper()
    hist_in_range = [t for t in hist_trades if t[0] >= start and t[0] <= end]
    ours_in_range = [t for t in our_trades if t[0] >= start and t[0] <= end]

    for t in hist_in_range:
        if t not in ours_in_range:
            print 'Hist Trade not in ours: %s' % t

    for t in ours_in_range:
        if t not in hist_in_range:
            print'Our trade not in history: %s' % t
    print'\n\n\n\n\n'
