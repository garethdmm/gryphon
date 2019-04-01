"""
Our first fundamental value version used for the multi algorithm.
"""

from gryphon.lib.exchange.retry import exchange_retry
from gryphon.lib.money import Money


@exchange_retry()
def calculate(algo, fundamental_value_balance_map):
    """
    Using the fundamental value balance map, the core fundamental value is the fiat-
    capital-weighted average of the fundamental values.
    """
    buffer_value = algo.config['volume_currency_buffer_value']

    algo.log(
        'buffer_value:%s USD:%s' % (buffer_value, buffer_value.to('USD')),
        log_level='debug',
    )

    bid_fundamental_value = Money('0', 'USD')
    ask_fundamental_value = Money('0', 'USD')

    bid_participating_exchanges = []
    ask_participating_exchanges = []

    bid_maximum_sum = Money('0', 'USD')
    ask_maximum_sum = Money('0', 'USD')

    # Determine which exchanges should participate in the bid and which in the ask
    # and sum them up appropriately.
    for exchange_name, exchange in fundamental_value_balance_map.iteritems():
        # You may sell if you have enough bitcoin to place an order and don't have
        # too much fiat.
        if (exchange[algo.volume_currency.lower()] > buffer_value and
                exchange['fiat'] + buffer_value.to('USD') < exchange['maximum'] and
                'bid_quote' in exchange and
                exchange['bid_quote']):
            ask_participating_exchanges.append(exchange_name)
            ask_maximum_sum += exchange['maximum']

        # You may buy if you have enough fiat.
        if (exchange['fiat'] > buffer_value.to('USD') and
                'ask_quote' in exchange and
                 exchange['ask_quote']):
            bid_participating_exchanges.append(exchange_name)
            bid_maximum_sum += exchange['maximum']

    for exchange_name in bid_participating_exchanges:
        exchange = fundamental_value_balance_map[exchange_name]
        bid_fundamental_value += (
            exchange['ask_quote'] * (exchange['maximum'] / bid_maximum_sum)
        )

    for exchange_name in ask_participating_exchanges:
        exchange = fundamental_value_balance_map[exchange_name]
        ask_fundamental_value += (
            exchange['bid_quote'] * (exchange['maximum'] / ask_maximum_sum)
        )

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

