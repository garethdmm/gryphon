# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.trades_poller import TradesPoller
from gryphon.lib.money import Money


class BitfinexTrades(TradesPoller):
    """
    Bitfinex's trades endpoint currently has a rate limit of 45/minute.

    This endpoint operates by returning the last n trades when it is called, with
    n=50 as the default. There is also an option to only return trades after a given
    timestamp. Both of these pieces of functionality are unimplemented currently.
    """

    def __init__(self):
        self.exchange_name = u'BITFINEX_BTC_USD'
        self.url = 'https://api.bitfinex.com/v1/trades/btcusd'
        self.poll_time = 4

    def parse_trades(self, resp_obj):
        trades = []

        for trade in resp_obj:
            trade = {
                'exchange': self.exchange_name,
                'price': Money(trade['price'], 'USD'),
                'volume': Money(trade['amount'], 'BTC'),
                'timestamp': trade['timestamp'],
                'trade_id': trade['tid']
            }

            trades.append(trade)

        return trades
