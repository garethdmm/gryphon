"""
A simple utility that collects the entire ledger for an exchange account for a given
period and outputs it in .csv format. Very useful for year-end accounting.
"""

import pytz
import sys

# TODO: this script should do it's own imports, not rely on the console.
from gryphon.execution.console import *

import gryphon.lib.exchange.exchange_factory as exchange_factory
from gryphon.lib.time_parsing import parse


# This dictionary should be a list of [blockchain address]:exchange_name pairs, mapping
# the addresses which you use to move crypto-assets between exchanges to the exchange
# names. It's useful to have crypto deposits/withdrawals identified by where the asset
# was going in the ledger.
address_map = {
    u'1234567890bcdefghijklmnopqrstuvwxy': u'BITSTAMP',
}


def get_ledger_table_for_time(exchange_name, start_time, end_time, currency=None):
    if currency:
        currency = currency.upper()

    exchange_name = exchange_name.capitalize()
    exchange = exchange_factory.make_exchange_from_key(exchange_name)

    exchange_data = exchange_factory.make_exchange_data_from_key(
        exchange_name,
        db,
    )

    fiat_currency = exchange.currency

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
    ledger_diff = exchange_data.ledger_balance(
        start_time=start_time,
        end_time=end_time,
    )
    ending_ledger_balance = starting_ledger_balance + ledger_diff

    ledger_table = []

    for entry in ledger:
        if isinstance(entry, Trade):
            table_entries = table_entries_from_trade(entry)
        elif isinstance(entry, Transaction):
            table_entries = table_entries_from_transaction(entry)

        ledger_table += table_entries

    #ledger_table = self.filter_to_currency(ledger_table, currency)

    current_balance = starting_ledger_balance

    for table_entry in reversed(ledger_table):
        if 'credit' in table_entry:
            current_balance += table_entry['credit']
        if 'debit' in table_entry:
            current_balance -= table_entry['debit']

        table_entry['balance'] = current_balance

    return fiat_currency, currency, ledger_table


def table_entries_from_trade(trade):
    entries = []

    if trade.trade_type == Trade.BID:
        desc = 'Trade #%s: Buy %s for %s' % (trade.exchange_trade_id, trade.volume, trade.price)
        entries.append({
            'credit': trade.volume,
            'description': desc,
            'type': 'Trade - BUY'
        })
        entries.append({'debit': trade.price, 'description': desc, 'type': 'Trade - BUY'})

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
        entries.append({'debit': trade.volume, 'description': desc, 'type': 'Trade - SELL'})

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


def table_entries_from_transaction(transaction):
    entries = []

    if 'drift' in transaction.transaction_details:
        # Skipping Drift Transactions
        return entries

    if transaction.transaction_type == Transaction.WITHDRAWL:
        deposit_address = transaction.transaction_details.get('deposit_address')
        destination = get_exchange_for_address(deposit_address)
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


def get_exchange_for_address(address):

    if address and address in address_map:
        return address_map[address]
    else:
        return 'Non Exchange Transfer or Unknown Address'


def export_ledger_for_exchange(exchange_name, start_time, end_time):
    exchange_obj = exchange_factory.make_exchange_from_key(exchange_name)

    lines = 'Description, %s Credit, %s Debit, BTC Credit, BTC Debit, BTC Balance, %s Balance, Date (UTC)\n' % (exchange_obj.currency, exchange_obj.currency, exchange_obj.currency)

    _, _, ledger_table = get_ledger_table_for_time(exchange_name, start_time, end_time)

    for table_entry in ledger_table:
        fiat_debit = ''
        btc_debit = ''
        fiat_credit = ''
        btc_credit = ''

        if 'debit' in table_entry:
            if table_entry['debit'].currency == 'BTC':
                btc_debit = table_entry['debit'].amount
            else:
                fiat_debit = table_entry['debit'].amount

        if 'credit' in table_entry:
            if table_entry['credit'].currency == 'BTC':
                btc_credit = table_entry['credit'].amount
            else:
                fiat_credit = table_entry['credit'].amount

        btc_balance = table_entry['balance']['BTC'].amount

        fiat_balance = table_entry['balance'][exchange_obj.currency].amount

        date = table_entry.get('date')

        lines += '"%s",%s,%s,"%s","%s","%s","%s",%s\n' % (
            table_entry.get('description', ''),
            fiat_credit,
            fiat_debit,
            btc_credit,
            btc_debit,
            btc_balance,
            fiat_balance,
            date,
        )
    
    filename = '%s_ledger_%s_%s.csv' % (
        exchange_name.lower(),
        start_time.strftime('%Y-%m-%d'),
        end_time.strftime('%Y-%m-%d'),
    )

    f = open(filename, 'w')
    f.write(lines)
    f.close()


def main(script_arguments, execute):
    exchange_name = script_arguments['exchange'].upper()
    start_str = script_arguments['start']
    end_str = script_arguments['end']

    start_time = parse(start_str).datetime
    end_time = parse(end_str).datetime

    export_ledger_for_exchange(exchange_name, start_time, end_time)

