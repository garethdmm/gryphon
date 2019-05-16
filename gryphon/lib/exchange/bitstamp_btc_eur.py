# -*- coding: utf-8 -*-
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.lib.money import Money


class BitstampBTCEURExchange(BitstampBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(BitstampBTCEURExchange, self).__init__(session)

        self.name = u'BITSTAMP_BTC_EUR'
        self.friendly_name = u'Bitstamp BTC-EUR'
        self.currency = u'EUR'
        self.volume_currency = 'BTC'
        self.price_decimal_precision = 2
        self.volume_decimal_precision = 8

        self.fiat_balance_tolerance = Money('0.0001', 'EUR')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.min_order_size = Money('0.001', 'BTC')

        if configuration:
            self.configure(configuration)

        self.ticker_url = 'ticker/btceur/'
        self.orderbook_url = 'order_book/btceur/'
        self.buy_url = 'buy/btceur/'
        self.sell_url = 'sell/btceur/'
        self.open_orders_url = 'open_orders/btceur/'
        self.trade_status_url = 'user_transactions/btceur/'
        self.balance_url = 'balance/'
        self.trade_cancel_url = 'cancel_order/'

