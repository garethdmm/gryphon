# -*- coding: utf-8 -*-
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.lib.money import Money


class BitstampBCHUSDExchange(BitstampBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(BitstampBCHUSDExchange, self).__init__(session)

        self.name = u'BITSTAMP_BCH_USD'
        self.friendly_name = u'Bitstamp BCH-USD'
        self.currency = u'USD'
        self.volume_currency = 'BCH'

        self.price_decimal_precision = 2
        self.volume_decimal_precision = 8

        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'BCH')
        self.min_order_size = Money('0.001', 'BCH')

        if configuration:
            self.configure(configuration)

        self.ticker_url = 'ticker/bchusd/'
        self.orderbook_url = 'order_book/bchusd/'
        self.buy_url = 'buy/bchusd/'
        self.sell_url = 'sell/bchusd/'
        self.open_orders_url = 'open_orders/bchusd/'
        self.trade_status_url = 'user_transactions/bchusd/'
        self.balance_url = 'balance/'
        self.trade_cancel_url = 'cancel_order/'
