"""
Reference for minimums: https://docs.gemini.com/rest-api/#symbols-and-minimums
"""
# -*- coding: utf-8 -*-
from gryphon.lib.exchange.gemini_btc_usd import GeminiBTCUSDExchange
from gryphon.lib.money import Money


class GeminiETHBTCExchange(GeminiBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(GeminiETHBTCExchange, self).__init__(session)
        self.name = u'GEMINI_ETH_BTC'
        self.friendly_name = u'Gemini ETH-BTC'
        self.currency = 'BTC'
        self.volume_currency = 'ETH'
        self.price_decimal_precision = 5
        self.volume_decimal_precision = 6
        self.gemini_pair_symbol = 'ethbtc'

        # Configurables with defaults.
        self.fiat_balance_tolerance = Money('0.0001', 'BTC')
        self.volume_balance_tolerance = Money('0.00000001', 'ETH')
        self.min_order_size = Money('0.001', 'ETH')

        if configuration:
            self.configure(configuration)

