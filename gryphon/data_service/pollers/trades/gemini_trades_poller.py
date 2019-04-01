# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.trades_poller import TradesPoller
from gryphon.lib.money import Money


class GeminiTrades(TradesPoller):
    def __init__(self):
        self.exchange_name = u'GEMINI_BTC_USD'
        self.url = 'https://api.gemini.com/v1/trades/BTCUSD?limit_trades=500'
        self.poll_time = 10

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
