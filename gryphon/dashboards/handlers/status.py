# -*- coding: utf-8 -*-
from datetime import timedelta
import logging

from delorean import Delorean
import tornado.web

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.models.order import Order
from gryphon.lib.models.exchange import Exchange as ExchangeData
from gryphon.lib.models.exchange import Balance
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money


logger = logging.getLogger(__name__)

BANK_ACCOUNT_HIGHLIGHT_THRESHOLD = 30000


class GryphonStatusHandler(AdminBaseHandler):
    @tornado.web.authenticated
    def get(self):
        exchanges = exchange_factory.get_all_initialized_exchange_wrappers(
            self.trading_db,
        )

        exchange_info = self.get_exchange_info(exchanges)
        system_balances, total_fiat = self.get_system_balances(exchanges)
        bank_accounts = self.get_trading_bank_accounts()
        in_transit_fiat_txs, in_transit_btc_txs = self.get_in_transit_transactions()
        recent_transactions = self.get_recent_transactions()
        net_flows = self.get_daily_net_transaction_flows(exchanges)

        self.render_template(
            'status.html',
            args={
                'all_exchanges': exchange_info,
                'system_balances': system_balances,
                'bank_accounts': bank_accounts,
                'total_fiat': total_fiat,
                'in_transit_fiat_txs': in_transit_fiat_txs,
                'in_transit_btc_txs': in_transit_btc_txs,
                'recent_transactions': recent_transactions,
                'net_flows': net_flows,
            },
        )

    def get_daily_net_transaction_flows(self, exchanges):
        flows = []
        one_day_ago = Delorean().last_day(1).naive

        for exchange in exchanges:
            exchange_data = exchange.exchange_account_db_object(self.trading_db)

            exchange_txs = exchange_data.transactions\
                .filter(Transaction._amount_currency == 'BTC')\
                .filter(Transaction.time_created > one_day_ago)\
                .filter(Transaction.transaction_status == 'COMPLETED')\
                .order_by(Transaction.time_created.desc())\
                .all()

            deposit_total = sum([
                round(tx.amount.amount, 0)
                for tx in exchange_txs if tx.transaction_type == Transaction.DEPOSIT
            ])

            withdrawal_total = sum([
                round(tx.amount.amount, 0)
                for tx in exchange_txs if tx.transaction_type == Transaction.WITHDRAWL
            ])

            flows.append({
                'exchange_name': exchange.name,
                'withdrawals': withdrawal_total,
                'deposits': deposit_total,
            })

        flows = sorted(
            flows,
            key=lambda flow: flow.get('withdrawals') + flow.get('deposits'),
            reverse=True
        )

        return flows

    def get_recent_transactions(self):
        five_hours_ago = Delorean().naive - timedelta(hours=5)

        txs = self.trading_db.query(Transaction)\
            .filter(Transaction.time_created > five_hours_ago)\
            .filter_by(transaction_status='COMPLETED')\
            .order_by(Transaction.time_created.desc())\
            .join(ExchangeData)\
            .all()

        return txs

    def get_in_transit_transactions(self):
        """
        Query all IN_TRANSIT transactions from the database.

        Returns the fiat tx results, and then the btc ones
        """
        all_txs_query = self.trading_db.query(Transaction)\
            .filter_by(transaction_status='IN_TRANSIT')\
            .join(ExchangeData)\
            .order_by(Transaction.time_created)

        fiat_txs = all_txs_query.filter(Transaction._amount_currency != "BTC").all()
        btc_txs = all_txs_query.filter(Transaction._amount_currency == "BTC").all()

        return fiat_txs, btc_txs

    def get_exchange_info(self, exchanges):
        up_exchanges = self.get_up_exchanges()

        exchange_info = []

        for exchange in exchanges:
            exchange_data = exchange.exchange_account_db_object(self.trading_db)
            exchange_dict = {
                'name': exchange.name,
                'balance': exchange_data.balance,
                'is_up': exchange.name in up_exchanges.keys(),
                'up_since': up_exchanges.get(exchange.name),
            }

            exchange_info.append(exchange_dict)

        exchange_info = sorted(exchange_info, key=lambda e: e.get('is_up') is False)

        return exchange_info

    def get_system_balances(self, exchanges):
        system_balance = Balance()

        for e in exchanges:
            system_balance += e.exchange_account_db_object(self.trading_db).balance

        total_fiat = sum([
            balance.to("USD") for currency, balance in system_balance.iteritems()
            if currency not in Money.CRYPTO_CURRENCIES
        ])

        return system_balance, total_fiat

    def get_up_exchanges(self):
        now = Delorean().naive
        ten_minutes_ago = now - timedelta(minutes=10)

        orders = self.trading_db\
            .query(Order)\
            .filter(Order.time_created > ten_minutes_ago)\
            .order_by(Order.time_created.asc())\
            .all()

        up_exchanges = {}

        for order in orders:
            up_exchanges[order._exchange_name] = order.time_created

        # TODO: convert these into "minutes ago".
        for key in up_exchanges.keys():
            up_exchanges[key] = now - up_exchanges[key]

        return up_exchanges

    def get_trading_bank_accounts(self):
        trading_bank_acount_keys = ['BMO_USD', 'BMO_CAD']

        bank_account_infos = []

        for key in trading_bank_acount_keys:
            account = exchange_factory.make_exchange_data_from_key(
                key,
                self.trading_db,
            )

            account_info = {
                'name': account.name,
                'balance': account.balance.fiat(),
                'highlight': account.balance.fiat() > BANK_ACCOUNT_HIGHLIGHT_THRESHOLD,
            }
            bank_account_infos.append(account_info)

        return bank_account_infos

