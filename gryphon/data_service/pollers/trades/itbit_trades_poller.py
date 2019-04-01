# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.trades_poller import TradesPoller
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse


class ItbitTrades(TradesPoller):
    def __init__(self):
        self.exchange_name = u'ITBIT_BTC_USD'
        self.url = 'https://api.itbit.com/v1/markets/XBTUSD/trades?since=0'
        self.poll_time = 10

    def parse_trades(self, resp_obj):
        raw_trades = resp_obj['recentTrades']
        trades = []

        for raw_trade in raw_trades:
            trade = {
                'exchange': self.exchange_name,
                'price': Money(raw_trade['price'], 'USD'),
                'volume': Money(raw_trade['amount'], 'BTC'),
                'timestamp': parse(raw_trade['timestamp']).epoch,
                'trade_id': raw_trade['matchNumber'],
            }

            trades.append(trade)

        return trades
