"""
Precisions and limits are available at:
https://www.bitstamp.net/api/v2/trading-pairs-info/
"""
# -*- coding: utf-8 -*-
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.lib.money import Money


class BitstampBCHBTCExchange(BitstampBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(BitstampBCHBTCExchange, self).__init__(session)

        self.name = u'BITSTAMP_BCH_BTC'
        self.friendly_name = u'Bitstamp BCH-BTC'
        self.currency = u'BTC'
        self.volume_currency = 'BCH'

        self.price_decimal_precision = 8
        self.volume_decimal_precision = 8

        self.fiat_balance_tolerance = Money('0.0001', 'BCH')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.min_order_size = Money('0.02', 'BCH')

        if configuration:
            self.configure(configuration)

        self.ticker_url = 'ticker/bchbtc/'
        self.orderbook_url = 'order_book/bchbtc/'
        self.buy_url = 'buy/bchbtc/'
        self.sell_url = 'sell/bchbtc/'
        self.open_orders_url = 'open_orders/bchbtc/'
        self.trade_status_url = 'user_transactions/bchbtc/'
        self.balance_url = 'balance/'
        self.trade_cancel_url = 'cancel_order/'

