"""
New fundamental value Sept 2016. Identical to V1 except it uses a list of
hardcoded weights based on exchange volumes instead of the maximum allowed
balance to determine the exchange weighting in the fundamental value
calculation.

TODO: If we like this, rip out cfv_v1.
"""

from cdecimal import Decimal

from gryphon.lib.exchange.retry import exchange_retry
from gryphon.lib.money import Money
from gryphon.execution.lib import conf


@exchange_retry()
def calculate(algo, fundamental_value_balance_map):
    buffer_value = algo.config['volume_currency_buffer_value']

    algo.log(
        'buffer_value:%s USD:%s' % (buffer_value, buffer_value.to('USD')),
        log_level='debug',
    )

    bid_fundamental_value = Money('0', 'USD')
    ask_fundamental_value = Money('0', 'USD')

    bid_participating_exchanges = []
    ask_participating_exchanges = []

    total_bid_weight = Decimal('0')
    total_ask_weight = Decimal('0')

    # Determine which exchanges should participate in the bid and which in the ask
    # and sum them up appropriately.
    for exchange_name, exchange in fundamental_value_balance_map.iteritems():
        # You may sell if you have enough bitcoin to place an order and don't have
        # too much fiat.
        exchange_weight = conf.fv_v3_weights[algo.volume_currency][exchange_name]

        if (exchange[algo.volume_currency.lower()] > buffer_value and
                exchange['fiat'] + buffer_value.to('USD') < exchange['maximum'] and
                'bid_quote' in exchange and
                exchange['bid_quote']):
            ask_participating_exchanges.append(exchange_name)
            total_ask_weight += exchange_weight

            algo.log(
                'Ask Weight: %s: %s' % (exchange_name, exchange_weight),
                log_level='debug',
            )

        # You may buy if you have enough fiat.
        if (exchange['fiat'] > buffer_value.to('USD') and
                'ask_quote' in exchange and
                 exchange['ask_quote']):
            bid_participating_exchanges.append(exchange_name)
            total_bid_weight += exchange_weight

            algo.log(
                'Bid Weight: %s: %s' % (exchange_name, exchange_weight),
                log_level='debug',
            )

    for exchange_name in bid_participating_exchanges:
        exchange = fundamental_value_balance_map[exchange_name]
        exchange_weight = conf.fv_v3_weights[algo.volume_currency][exchange_name]

        bid_fundamental_value += (
            exchange['ask_quote'] * (exchange_weight / total_bid_weight)
        )

    for exchange_name in ask_participating_exchanges:
        exchange = fundamental_value_balance_map[exchange_name]
        exchange_weight = conf.fv_v3_weights[algo.volume_currency][exchange_name]

        ask_fundamental_value += (
            exchange['bid_quote'] * (exchange_weight / total_ask_weight)
        )

    algo.log('Bid weights: %s' % total_bid_weight, log_level='debug')
    algo.log('Ask weights: %s' % total_ask_weight, log_level='debug')

    algo.log(
        'Bid Participating Exchanges: %s' % bid_participating_exchanges,
        log_level='debug',
    )

    algo.log(
        'Bid Fundamental Value: %s' % bid_fundamental_value,
        log_level='debug',
    )

    algo.log(
        'Ask Participating Exchanges: %s' % ask_participating_exchanges,
        log_level='debug',
    )

    algo.log(
        'Ask Fundamental value: %s' % ask_fundamental_value,
        log_level='debug',
    )

    if bid_participating_exchanges and ask_participating_exchanges:
        algo.log(
            'Using avg of bid and ask participating exchanges',
            log_level='debug',
        )

        return (bid_fundamental_value + ask_fundamental_value) / 2
    elif bid_participating_exchanges:
        algo.log('Using bid participating exchanges', log_level='debug')

        return bid_fundamental_value
    elif ask_participating_exchanges:
        algo.log('Using ask participating exchanges', log_level='debug')

        return ask_fundamental_value
    else:
        raise Exception('No exchanges to calculate fundamental value')

