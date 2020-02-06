# -*- coding: utf-8 -*-
from gryphon.lib.exchange.bitstamp_btc_usd import BitstampBTCUSDExchange
from gryphon.lib.money import Money


class BitstampETHUSDExchange(BitstampBTCUSDExchange):
    def __init__(self, session=None, configuration=None):
        super(BitstampETHUSDExchange, self).__init__(session)

        self.name = u'BITSTAMP_ETH_USD'
        self.friendly_name = u'Bitstamp ETH-USD'
        self.currency = u'USD'
        self.volume_currency = 'ETH'

        self.fiat_balance_tolerance = Money('0.0001', 'USD')
        self.volume_balance_tolerance = Money('0.00000001', 'ETH')
        self.min_order_size = Money('0.15', 'ETH')
        # NOTE: min orders are $25 USD, this is $29 (2/20) for safety

        if configuration:
            self.configure(configuration)

        # Endpoints.
        # TODO: Implement deposit/withdrawal urls for bitstamp eth usd.
        self.withdrawl_requests_url = ''
        self.deposit_address_url = ''

        self.ticker_url = 'ticker/ethusd/'
        self.orderbook_url = 'order_book/ethusd/'
        self.buy_url = 'buy/ethusd/'
        self.sell_url = 'sell/ethusd/'
        self.open_orders_url = 'open_orders/ethusd/'
        self.trade_status_url = 'user_transactions/ethusd/'
        self.balance_url = 'balance/'
        self.trade_cancel_url = 'cancel_order/'

