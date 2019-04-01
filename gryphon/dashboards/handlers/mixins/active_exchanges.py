"""
Just a quick mixing for parsing a list of exchanges out of the querystring.
"""

DEFAULT_EXCHANGES = ['BITSTAMP', 'ITBIT', 'GEMINI']


class ActiveExchangesMixin():
    def get_active_exchanges(self, custom_defaults=None):
        raw_active_exchanges = self.get_argument('exchanges', None)
        active_exchanges = self.parse_active_exchanges(
            raw_active_exchanges,
            custom_defaults,
        )

        return active_exchanges

    def parse_active_exchanges(self, query_param, custom_defaults=None):
        if query_param is None:
            if custom_defaults is not None:
                return custom_defaults
            else:
                return DEFAULT_EXCHANGES
        else:
            exchange_names = query_param.split(',')
            exchange_names = [e.upper() for e in exchange_names]

            return exchange_names
