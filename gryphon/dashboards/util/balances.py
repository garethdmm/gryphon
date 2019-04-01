from collections import defaultdict
import json

from delorean import Delorean

from gryphon.lib.models.exchange import Balance
from gryphon.lib.money import Money
from gryphon.lib.models.event import Event
from gryphon.lib.models.exchange import Balance


def get_balance_time_series_from_audits(audits):
    fiat_balances = []
    btc_balances = []
    
    for audit in audits:
        timestamp = int(Delorean(audit.time_created, "UTC").epoch) * 1000

        # load the fiat and btc balances from the audit data
        data = json.loads(audit.data)

        try:
            # Old data format from before Jan 28, 2015
            raw_fiat = data['exchange_balance']['fiat_available']
            raw_btc = data['exchange_balance']['btc_available']
            fiat = Money.loads(raw_fiat).to("USD")
            btc = Money.loads(raw_btc)

        except KeyError:
            # New data format from after Jan 28, 2015
            try:
                balance_data = data['balance_data']
            except KeyError:
                continue

            # convert to Money objects
            for currency, balance_str in balance_data.iteritems():
                balance_data[currency] = Money.loads(balance_str)

            balance = Balance(balance_data)
            fiat = balance.fiat().to('USD')
            btc = balance['BTC']

        fiat_datapoint = [
            timestamp,
            str(fiat.amount),
        ]

        fiat_balances.append(fiat_datapoint)

        btc_datapoint = [
            timestamp,
            str(btc.amount),
        ]

        btc_balances.append(btc_datapoint)

    return fiat_balances, btc_balances


def get_audits_for_exchange(db, exchange_name, start_time=None, end_time=None, data_filter=None):
    audit_query = db\
        .query(Event)\
        .filter(Event.event_type == 'AUDIT')\
        .filter(Event.exchange_name == exchange_name)\
        .filter(Event.time_created > start_time)\
        .filter(Event.time_created < end_time)

    if data_filter:
        audit_query = audit_query.filter(Event.data.contains(data_filter))

    audits = audit_query.all()

    return audits


def get_all_audits_in_period(db, start_time, end_time, data_filter=None):
    audit_query = db\
        .query(Event)\
        .filter(Event.event_type == 'AUDIT')\
        .filter(Event.time_created > start_time)\
        .filter(Event.time_created < end_time)

    if data_filter:
        audit_query = audit_query.filter(Event.data.contains(data_filter))

    audits = audit_query.all()

    return audits


def get_balance_time_series_for_exchange(db, exchange_name, start_time, end_time):
    audits = get_audits_for_exchange(db, exchange_name, start_time, end_time)
    series = get_balance_time_series_from_audits(audits)

    return series


def get_drift_from_audits(audits):
    drift_by_currency = Balance()

    for audit in audits:
        if 'drift' in audit.data:
            data = json.loads(audit.data)

            for currency, str_amount in data['drift'].iteritems():
                drift_by_currency += Money.loads(str_amount)

    return drift_by_currency


def get_total_drift_in_period(db, start_time, end_time):
    audits = get_all_audits_in_period(db, start_time, end_time, data_filter='drift')

    return get_drift_from_audits(audits)


def get_drift_for_exchange_in_period(db, exchange_name, start_time, end_time):
    audits = get_audits_for_exchange(db, exchange_name, start_time, end_time, data_filter='drift')

    return get_drift_from_audits(audits)
