"""
Our second run at a fundamental value claculator, a bit smarter.
"""

from gryphon.lib.exchange.retry import exchange_retry
from gryphon.lib.money import Money
from gryphon.execution.lib import conf


@exchange_retry()
def calculate(algo, fundamental_value_balance_map):
    """
    Weighted fundamental value including only exchanges that can both buy and sell.
    """
    # TODO - store the buffer value in a config or some other thoughtout way.
    buffer_value = algo.config['volume_currency_buffer_value']

    weighted_fundamental_value = 0
    weight_sum = 0

    participating_exchanges = []

    for exchange_name, exchange in fundamental_value_balance_map.iteritems():
        # If you have bitcoin and are below your maximum fiat, you can sell.
        can_sell = (
            exchange[algo.volume_currency.lower()] > buffer_value and
            exchange['fiat'] < exchange['maximum'] - buffer_value.to('USD') and
            'bid_quote' in exchange and
            exchange['bid_quote']
        )

        # If you have enough fiat you can buy.
        can_buy = (
            exchange['fiat'] > buffer_value.to('USD') and
            'ask_quote' in exchange and
            exchange['ask_quote']
        )

        if can_sell and can_buy:
            participating_exchanges.append(exchange_name)
            weight_sum += conf.fv_v2_weights[algo.volume_currency][exchange_name]

    if not participating_exchanges:
        raise Exception('No exchanges to calculate fundamental value')

    trusted_exchanges = [
        e.strip().upper() for e in algo.config['trusted_exchanges'].split(',')
    ]

    if not any([e in trusted_exchanges for e in participating_exchanges]):
        raise Exception('No trusted exchanges in participating_exchanges')

    for exchange_name in participating_exchanges:
        exchange = fundamental_value_balance_map[exchange_name]
        exchange_fv = (exchange['ask_quote'] + exchange['bid_quote']) / 2
        exchange_weight = conf.fv_v2_weights[algo.volume_currency][exchange_name]
        normalized_weight = exchange_weight / weight_sum

        weighted_fundamental_value += exchange_fv * normalized_weight

    algo.log('Participating Exchanges: %s', participating_exchanges, 'yellow')

    return weighted_fundamental_value, participating_exchanges

