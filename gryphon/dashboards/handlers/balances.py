# -*- coding: utf-8 -*-
import logging

from delorean import Delorean
import tornado.web

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.dashboards.handlers.mixins.start_and_end_time import StartAndEndTimeMixin
import gryphon.dashboards.util.balances as balance_util
from gryphon.dashboards.util import queries
from gryphon.lib.exchange.exchange_factory import all_exchanges
from gryphon.lib.models.transaction import Transaction


logger = logging.getLogger(__name__)


class AllBalancesHandler(AdminBaseHandler, StartAndEndTimeMixin):
    @tornado.web.authenticated
    def get(self, month=None):
        start_time, end_time = self.get_start_time_and_end_time()

        start_time = queries.strip_datetime_for_db_operations(start_time)
        end_time = queries.strip_datetime_for_db_operations(end_time)

        start_timestamp = Delorean(start_time, 'UTC').epoch * 1000
        end_timestamp = Delorean(end_time, 'UTC').epoch * 1000

        usd_balances_series = {}
        btc_balances_series = {}

        for exchange in all_exchanges():
            usd_balances, btc_balances = balance_util.get_balance_time_series_for_exchange(self.trading_db, exchange.name, start_time, end_time)

            usd_balances_series[exchange.name] = usd_balances
            btc_balances_series[exchange.name] = btc_balances

        withdrawals = self.trading_db\
            .query(Transaction)\
            .filter(Transaction.time_created >= start_time)\
            .filter(Transaction.time_created < end_time)\
            .filter(Transaction._amount_currency == 'BTC')\
            .filter(Transaction.transaction_type == 'WITHDRAWL')\
            .all()

        deposits = self.trading_db\
            .query(Transaction)\
            .filter(Transaction.time_created >= start_time)\
            .filter(Transaction.time_created < end_time)\
            .filter(Transaction._amount_currency == 'BTC')\
            .filter(Transaction.transaction_type == 'DEPOSIT')\
            .all()

        bitcoin_withdrawals = [[int(Delorean(movement.time_created, "UTC").epoch) * 1000, float(movement.amount.amount)] for movement in withdrawals]

        bitcoin_deposits = [[int(Delorean(movement.time_created, "UTC").epoch) * 1000, float(movement.amount.amount)] for movement in deposits]

        self.render_template(
            'balances.html',
            args={
                'usd_balances_series': usd_balances_series,
                'btc_balances_series': btc_balances_series,
                'bitcoin_withdrawals': bitcoin_withdrawals,
                'bitcoin_deposits': bitcoin_deposits,
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
            },
        )

