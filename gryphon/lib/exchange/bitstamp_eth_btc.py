# -*- coding: utf-8 -*-
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.lib.money import Money


class BitstampETHBTCExchange(BitstampBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(BitstampETHBTCExchange, self).__init__(session)

        self.name = u'BITSTAMP_ETH_BTC'
        self.friendly_name = u'Bitstamp ETH-BTC'
        self.currency = u'BTC'
        self.volume_currency = 'ETH'

        self.price_decimal_precision = 5
        self.volume_decimal_precision = 8

        self.fiat_balance_tolerance = Money('0.0001', 'BTC')
        self.volume_balance_tolerance = Money('0.00000001', 'ETH')
        self.min_order_size = Money('0.03', 'ETH')

        if configuration:
            self.configure(configuration)

        self.ticker_url = 'ticker/ethbtc/'
        self.orderbook_url = 'order_book/ethbtc/'
        self.buy_url = 'buy/ethbtc/'
        self.sell_url = 'sell/ethbtc/'
        self.open_orders_url = 'open_orders/ethbtc/'
        self.trade_status_url = 'user_transactions/ethbtc/'
        self.balance_url = 'balance/'
        self.trade_cancel_url = 'cancel_order/'
