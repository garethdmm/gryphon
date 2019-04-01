from collections import OrderedDict

from gryphon.lib.exchange import exchange_factory


def load_exchange_names(db):
    exchanges = exchange_factory.get_all_initialized_exchange_wrappers(db)
    exchange_names = OrderedDict()

    exchanges = sorted(exchanges, key=lambda e: e.friendly_name)

    for exchange in exchanges:
        exchange_names[exchange.name.lower()] = exchange.friendly_name

    return exchange_names
