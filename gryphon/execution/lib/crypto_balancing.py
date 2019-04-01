import hashlib

from cdecimal import *
from delorean import Delorean

from gryphon.execution.lib import conf
from gryphon.lib.exchange.exchange_factory import make_exchange_from_key
from gryphon.lib.logger import get_logger
from gryphon.lib.money import Money
from gryphon.lib.models.exchange import Exchange
from gryphon.lib.models.exchange import Transaction
from gryphon.lib.session import commit_mysql_session
from gryphon.lib.util.profile import tick_profile

logger = get_logger(__name__)

TRANSFER_UNIT = Money('30', 'BTC')


# this gives us a unique amount to add to withdrawal transactions
# they will look like 10.00xxxx00 where xxxx is the unique number
# we can't use the last 2 decimals because of OkCoin's balance rounding
def create_uniquifier():
    hasher = hashlib.sha1()
    hasher.update(str(Delorean().epoch))
    uniquifier = int(hasher.hexdigest(), 16) % 10000
    uniquifier *= Decimal("0.000001")
    assert(uniquifier < Decimal("0.01"))
    return uniquifier


def get_deposit_enabled_exchanges(db):
    exchange_targets = db.query(Exchange)\
        .filter(Exchange.name.in_(conf.deposits_enabled))\
        .all()

    return exchange_targets


def get_destination_exchange(algo, exchange_data, exchanges):
    full_balances = {}

    for exchange in exchanges:
        full_balances[exchange.name] = exchange.full_balance
        
    bitcoin_total = sum([full_balances[e.name]['BTC'] for e in exchanges])

    rules = {}

    # target == proportion of total bitcoins and max is TRANSFER_UNIT + target
    for exchange in exchanges:
        target = conf.proportions[exchange.name] * bitcoin_total
        maximum = TRANSFER_UNIT + target
        rules[exchange.name] = {'target': target, 'max': maximum}

        algo.log('%s - Bal:%s - w/inc:%s - Target:%s - Max BTC:%s', (exchange.name, exchange.balance['BTC'], full_balances[exchange.name]['BTC'], target, maximum ), 'yellow', log_level='debug')
   
    if exchange_data.balance['BTC'] < rules[exchange_data.name]['max']:
        algo.log('%s is not above its maximum (%s), not sending BTC', (exchange_data.name, rules[exchange_data.name]['max']), 'yellow')

        return
   
    # remove all exchanges with more than their target
    exchanges = [e for e in exchanges if full_balances[e.name]['BTC'] < rules[e.name]['target']]

    # remove exchanges with more than their maxiumum allowed total capital
    for e in exchanges:
        if full_balances[e.name].total_usd_value() >= conf.account_value_limits[e.name]:
            algo.log("Filtering out %s due to account value (%s) above limit (%s)", (e.name, full_balances[e.name].total_usd_value(), conf.account_value_limits[e.name]), 'yellow', log_level='debug')

    exchanges = [e for e in exchanges if full_balances[e.name].total_usd_value() < conf.account_value_limits[e.name]]
    
    # remove exchanges that our current bot isn't allowed to send to
    exchanges = [e for e in exchanges if e.name not in conf.forbidden_targets[exchange_data.name]]

    if not exchanges:
        algo.log('No Exchanges to Send BTC', (), 'yellow')
        return
    
    # sort exchanges into order by how close they are to their target
    exchanges.sort(key=lambda e: (full_balances[e.name]['BTC'] / rules[e.name]['target']))
    
    destination_exchange_data = exchanges[0] 

    return destination_exchange_data


def send_btc_from_exchange_to_exchange(self, source_exchange, destination_exchange, amount):
    raise Exception("""The code in the gryphon framework for transferring crypto
        around does not have a running test suite and should be used with caution. If
        you wish to use these features, simply remove this warning from your own copy
        of the codebase.""")

    destination_address = destination_exchange.current_deposit_address

    logger.info('Sending %s from %s to %s (%s)' % (
        amount,
        source_exchange.name,
        destination_exchange.name,
        destination_address,
    ))

    slacker = Slacker('#balancer','balancer', icon_emoji=':zap:')
    slacker.notify('Sending %s from %s to %s (%s)' % (
        amount,
        source_exchange.name,
        destination_exchange.name,
        destination_address,
    ))

    result = source_exchange.withdraw_crypto(destination_address, amount)

    return (
        destination_address,
        result.get('tx'),
        result.get('exchange_withdrawal_id'),
    )

@tick_profile
def bitcoin_rebalance(db, exchange_data, algo, execute=False):
    algo.log('------- Bitcoin Balancer Report -----------', (), 'yellow')

    if exchange_data.name not in conf.withdrawals_enabled:
        algo.log('Withdrawals not enabled for %s, not balancing', exchange_data.name, 'yellow')
        return
    
    exchanges = get_deposit_enabled_exchanges(db)

    destination_exchange_data = get_destination_exchange(algo, exchange_data, exchanges)

    if destination_exchange_data is None:
        return
    elif destination_exchange_data == exchange_data:
        algo.log('%s not sending to self', exchange_data.name, 'yellow')
        return
    
    source_exchange = make_exchange_from_key(exchange_data.name)
    destination_exchange = make_exchange_from_key(destination_exchange_data.name)

    transfer_amount = TRANSFER_UNIT + create_uniquifier()

    algo.log('Sending %s from %s to %s', (transfer_amount, source_exchange.name, destination_exchange.name), 'yellow')

    if execute:
        # Send the bitcoins and record the transactions.

        deposit_address, transaction_hash, exchange_withdrawal_id = send_btc_to_exchange(source_exchange, destination_exchange, transfer_amount)

        transactions = exchange_data.record_withdrawal(
            destination_exchange_data,
            transfer_amount,
            deposit_address,
            transaction_hash,
            exchange_withdrawal_id,
        )

        commit_mysql_session(db)
    else:
        algo.log('Not Sending Because of NO EXECUTE', (), 'yellow')

