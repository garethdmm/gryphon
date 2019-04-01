# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.trades_poller import TradesPoller
from gryphon.lib.money import Money


class OkcoinTrades(TradesPoller):
    def __init__(self):
        self.exchange_name = u'OKCOIN_BTC_USD'
        self.url = 'https://www.okcoin.com/api/trades.do?since=0&ok=1'
        self.poll_time = 1

    def parse_trades(self, resp_obj):
        trades = []

        for trade in resp_obj:
            trade = {
                'exchange': self.exchange_name,
                'price': Money(trade['price'], 'USD'),
                'volume': Money(trade['amount'], 'BTC'),
                'timestamp': trade['date'],
                'trade_id': trade['tid'],
            }

            trades.append(trade)

        return trades
