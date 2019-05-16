# -*- coding: utf-8 -*-
from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.lib.money import Money


class GeminiZECUSDExchange(GeminiBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(GeminiZECUSDExchange, self).__init__(session)

        self.name = u'GEMINI_ZEC_USD'
        self.friendly_name = u'Gemini ZEC-USD'
        self.currency = 'USD'
        self.volume_currency = 'ZEC'
        self.volume_decimal_precision = 6
        self.gemini_pair_symbol = 'zecusd'

        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'ETH')
        self.min_order_size = Money('0.001', 'ZEC')

        if configuration:
            self.configure(configuration)

