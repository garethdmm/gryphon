# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.trades_poller import TradesPoller
from gryphon.lib.money import Money


class BitstampTrades(TradesPoller):
    def __init__(self):
        self.exchange_name = u'BITSTAMP_BTC_USD'
        self.url = 'https://priv-api.bitstamp.net/api/transactions/?time=hour'
        self.poll_time = 10

    def parse_trades(self, resp_obj):
        trades = []

        for raw_trade in resp_obj:
            trade = {
                'exchange': self.exchange_name,
                'price': Money(raw_trade['price'], 'USD'),
                'volume': Money(raw_trade['amount'], 'BTC'),
                'timestamp': int(raw_trade['date']),
                'trade_id': raw_trade['tid'],
            }

            trades.append(trade)

        return trades
