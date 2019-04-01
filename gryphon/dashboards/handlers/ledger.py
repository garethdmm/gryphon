# -*- coding: utf-8 -*-
import datetime
import pytz
import os

import tornado.web

from gryphon.dashboards.handlers.admin_base import AdminBaseHandler
from gryphon.dashboards.handlers.mixins.start_and_end_time import StartAndEndTimeMixin
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.logger import get_logger
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.transaction import Transaction

logger = get_logger(__name__)

interval = datetime.timedelta(seconds=86400)
pwd = os.path.dirname(os.path.realpath(__file__))


class LedgerHandler(AdminBaseHandler, StartAndEndTimeMixin):
    def __init__(self, *args, **kwargs):
        super(LedgerHandler, self).__init__(*args, **kwargs)

        # This dictionary maps bitcoin addresses to exchange names.
        # TODO: Make this user-configurable.
        self.address_map = {}

    @tornado.web.authenticated
    def get(self, exchange_name=None, currency=None):
        exchange_name = exchange_name.upper()
        start_time, end_time = self.get_start_time_and_end_time()

        if (exchange_name
                not in exchange_factory.initialized_ledgers(self.trading_db)):
            self.redirect('/404')
            return

        fiat_currency, currency, ledger_table = self.get_ledger_table_for_time(
            exchange_name,
            start_time,
            end_time,
            currency,
        )

        self.render_template(
            'ledger.html',
            args={
                'exchange_name': exchange_name,
                'fiat_currency': fiat_currency,
                'currency': currency,
                'ledger_table': ledger_table,
            },
        )

    def get_ledger_table_for_time(self, exchange_name, start_time, end_time, currency=None):
        if currency:
            currency = currency.upper()

        exchange_name = exchange_name.capitalize()
        exchange = exchange_factory.make_exchange_from_key(exchange_name)
        exchange_data = exchange_factory.make_exchange_data_from_key(
            exchange_name,
            self.trading_db,
        )

        if exchange:
            # Normal bitcoin exchange.
            fiat_currency = exchange.currency
        else:
            # Bank Accounts don't have exchange objects.
            fiat_currency = self.currency_for_bank_account(exchange_name)

            # Bank Accounts only have one currency, so we set a currency filter by
            # default. It just makes the UI look nicer instead of having an empty BTC
            # column.
            currency = fiat_currency

        ledger = exchange_data.ledger(
            start_time=start_time,
            end_time=end_time,
            currency=currency,
        )

        # ledger is empty for this time period.
        if len(ledger) == 0:
            return fiat_currency, currency, []

        # get the exchange balance from before these ledger entries started
        oldest_entry = ledger[-1]
        oldest_time = oldest_entry.time_created

        # There can be multiple entries at the same time
        entries_at_oldest_time = []

        for entry in ledger:
            if isinstance(entry, Trade) and entry.time_created == oldest_time:
                entries_at_oldest_time.append(entry)
            elif isinstance(entry, Transaction) and entry.time_completed == oldest_time:
                entries_at_oldest_time.append(entry)

        oldest_time = pytz.utc.localize(oldest_time)
        balance_at_oldest_time = exchange_data.ledger_balance(end_time=oldest_time)

        # balance_at_oldest_time includes all the entries_at_oldest_time
        # so we need to remove them to get the pre-ledger balance
        pre_ledger_balance = balance_at_oldest_time

        for entry in entries_at_oldest_time:
            pre_ledger_balance -= entry.position

        starting_ledger_balance = exchange_data.ledger_balance(end_time=start_time)

        ledger_table = []

        for entry in ledger:
            if isinstance(entry, Trade):
                table_entries = self.table_entries_from_trade(entry)
            elif isinstance(entry, Transaction):
                table_entries = self.table_entries_from_transaction(entry)

            ledger_table += table_entries

        ledger_table = self.filter_to_currency(ledger_table, currency)

        current_balance = starting_ledger_balance

        for table_entry in reversed(ledger_table):
            if 'credit' in table_entry:
                current_balance += table_entry['credit']
            if 'debit' in table_entry:
                current_balance -= table_entry['debit']

            table_entry['balance'] = current_balance

        return fiat_currency, currency, ledger_table

    def get_exchange_for_address(self, address):
        """
        TODO: allow users to configure a list of exchange deposit addresses at startup
          so we can tell the intended destination of withdrawals.
        """

        if address and address in self.address_map:
            return address_map[address]
        else:
            return 'External transfer'

    def currency_for_bank_account(self, bank_account_name):
        """
        Get the operating currency of our bank accounts.

        Hacky, but I don't want to add exchange objects for all of these
        """
        if bank_account_name.upper() in ['BMO_CAD', 'BMO_CAD_OPS']:
            return 'CAD'
        else:
            return 'USD'

    def filter_to_currency(self, ledger_table, currency):
        if not currency:
            return ledger_table

        filtered_table = []
        for entry in ledger_table:
            if ('credit' in entry and entry['credit'].currency == currency
                    or 'debit' in entry and entry['debit'].currency == currency):
                filtered_table.append(entry)

        return filtered_table

    def table_entries_from_trade(self, trade):
        entries = []

        if trade.trade_type == Trade.BID:
            desc = 'Trade #%s: Buy %s for %s' % (
                trade.exchange_trade_id,
                trade.volume,
                trade.price,
            )

            entries.append({
                'credit': trade.volume,
                'description': desc,
                'type': 'Trade - BUY'
            })
            entries.append({
                'debit': trade.price,
                'description': desc,
                'type': 'Trade - BUY',
            })

        elif trade.trade_type == Trade.ASK:
            desc = 'Trade #%s: Sell %s for %s' % (
                trade.exchange_trade_id,
                trade.volume,
                trade.price,
            )
            entries.append({
                'credit': trade.price,
                'description': desc,
                'type': 'Trade - SELL'
            })
            entries.append({
                'debit': trade.volume,
                'description': desc,
                'type': 'Trade - SELL',
            })

        if trade.fee:
            entries.append({
                'debit': trade.fee,
                'description': 'Trade #%s: Fee' % trade.exchange_trade_id,
                'type': 'Trade - FEE',
            })

        date = trade.time_created
        for entry in entries:
            entry['date'] = date
            entry['details'] = ''

        return entries

    def table_entries_from_transaction(self, transaction):
        entries = []

        if 'drift' in transaction.transaction_details:
            # Skipping Drift Transactions
            return entries

        if transaction.transaction_type == Transaction.WITHDRAWL:
            deposit_address = transaction.transaction_details.get('deposit_address')
            destination = self.get_exchange_for_address(deposit_address)
            desc = 'Withdrawal to %s' % destination

            entries.append({
                'debit': transaction.amount,
                'description': desc,
                'type': 'Withdrawal - %s' % destination,
            })

        elif transaction.transaction_type == Transaction.DEPOSIT:
            desc = 'Deposit'
            entries.append({
                'credit': transaction.amount,
                'description': desc,
                'type': 'Deposit',
            })

        if transaction.fee:
            entries.append({
                'debit': transaction.fee,
                'description': 'Transaction Fee',
                'type': 'Transaction Fee',
            })

        date = transaction.time_completed
        if not date:
            date = transaction.time_created
        for entry in entries:
            entry['date'] = date
            entry['details'] = ''.join([
                '%s:%s ' % (k, v)
                for k, v in transaction.transaction_details.iteritems()
                if k in ['external_transaction_id', 'notes'] and v not in ['xxx']
            ])

        return entries
