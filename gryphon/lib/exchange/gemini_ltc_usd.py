# -*- coding: utf-8 -*-
from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.lib.money import Money


class GeminiLTCUSDExchange(GeminiBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(GeminiLTCUSDExchange, self).__init__(session)

        self.name = u'GEMINI_LTC_USD'
        self.friendly_name = u'Gemini LTC-USD'
        self.currency = 'USD'
        self.volume_currency = 'LTC'
        self.volume_decimal_precision = 5
        self.gemini_pair_symbol = 'ltcusd'

        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'ETH')
        self.min_order_size = Money('0.01', 'LTC')

        if configuration:
            self.configure(configuration)

