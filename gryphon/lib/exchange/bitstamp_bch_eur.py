# -*- coding: utf-8 -*-
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.lib.money import Money


class BitstampBCHEURExchange(BitstampBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(BitstampBCHEURExchange, self).__init__(session)

        self.name = u'BITSTAMP_BCH_EUR'
        self.friendly_name = u'Bitstamp BCH-EUR'
        self.currency = u'EUR'
        self.volume_currency = 'BCH'

        self.price_decimal_precision = 2
        self.volume_decimal_precision = 8

        self.fiat_balance_tolerance = Money('0.0001', 'EUR')
        self.volume_balance_tolerance = Money('0.00000001', 'BCH')
        self.min_order_size = Money('0.001', 'BCH')

        if configuration:
            self.configure(configuration)

        self.ticker_url = 'ticker/bcheur/'
        self.orderbook_url = 'order_book/bcheur/'
        self.buy_url = 'buy/bcheur/'
        self.sell_url = 'sell/bcheur/'
        self.open_orders_url = 'open_orders/bcheur/'
        self.trade_status_url = 'user_transactions/bcheur/'
        self.balance_url = 'balance/'
        self.trade_cancel_url = 'cancel_order/'
