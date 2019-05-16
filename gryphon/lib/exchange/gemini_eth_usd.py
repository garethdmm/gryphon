# -*- coding: utf-8 -*-
from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.lib.money import Money


class GeminiETHUSDExchange(GeminiBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(GeminiETHUSDExchange, self).__init__(session)

        self.name = u'GEMINI_ETH_USD'
        self.friendly_name = u'Gemini ETH-USD'
        self.currency = 'USD'
        self.volume_currency = 'ETH'
        self.volume_decimal_precision = 6
        self.gemini_pair_symbol = 'ethusd'

        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'ETH')
        self.min_order_size = Money('0.001', 'ETH')

        if configuration:
            self.configure(configuration)

