import datetime

from delorean import Delorean

from gryphon.lib import assets
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.models.exchange import Balance


def get_liabilities_series(db, start_time, end_time):
    liabilities_series = []

    current_time = start_time

    while current_time <= end_time:
        debts = assets.get_active_liabilities(db, current_time)
        debt_balance = sum([d.amount for d in debts], Balance())

        liabilities_series.append((current_time, debt_balance))

        current_time += datetime.timedelta(days=1)

    return liabilities_series


def get_assets_series(db, start_time, end_time):
    account_keys = []

    account_keys = exchange_factory.initialized_ledgers(db)

    # The burn account is essentially a negative balance. Don't add it to our assets.
    if 'BURN' in account_keys:
        account_keys.remove('BURN')

    starting_balance = assets.ledger_balance(
        db,
        end_time=start_time,
        include_pending=True,
        exchange_names=account_keys,
    )

    assets_series = []

    current_time = start_time
    current_balance = starting_balance

    assets_series.append((current_time, current_balance))

    last_time = current_time
    current_time += datetime.timedelta(days=1)

    while current_time <= end_time:
        balance_diff = assets.ledger_balance(
            db,
            start_time=last_time,
            end_time=current_time,
            include_pending=True,
            exchange_names=account_keys,
        )
        current_balance += balance_diff

        assets_series.append((current_time, current_balance))

        last_time = current_time
        current_time += datetime.timedelta(days=1)

    return assets_series


def calculate_net_assets_series(assets_series, liabilities_series):
    assert(len(assets_series) == len(liabilities_series))

    net_assets_series = []
    for asset_datapoint, liability_datapoint in zip(assets_series, liabilities_series):
        assets_time, assets_balance = asset_datapoint
        liabilities_time, liabilities_balance = liability_datapoint

        net_assets_balance = assets_balance - liabilities_balance
        assert(assets_time == liabilities_time)
        net_assets_series.append((assets_time, net_assets_balance))

    return net_assets_series


def convert_balance_series_to_usd(balance_series):
    usd_series = []
    for datapoint in balance_series:
        time, balance = datapoint
        # Warning: historical exchange rate doesn't handle today
        usd_balance = balance.total_usd_value(date=time)
        usd_series.append((time, usd_balance))

    return usd_series


def process_usd_series_for_flot(usd_series):
    flot_series = []
    for datapoint in usd_series:
        time, usd_balance = datapoint

        flot_timestamp = int(Delorean(time, 'UTC').epoch) * 1000
        flot_usd_balance = float(usd_balance.amount)
        flot_datapoint = (flot_timestamp, flot_usd_balance)

        flot_series.append(flot_datapoint)

    return flot_series
