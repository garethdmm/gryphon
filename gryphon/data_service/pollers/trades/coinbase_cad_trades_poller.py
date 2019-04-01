# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.trades_poller import TradesPoller
from gryphon.lib.money import Money
from gryphon.lib.time_parsing import parse


class CoinbaseCadTrades(TradesPoller):
    def __init__(self):
        self.exchange_name = u'COINBASE_BTC_CAD'
        self.url = 'https://api.exchange.coinbase.com/products/BTC-CAD/trades'
        self.poll_time = 10

    def parse_trades(self, resp_obj):
        trades = []

        for trade in resp_obj:
            trade = {
                'exchange': self.exchange_name,
                'price': Money(trade['price'], 'CAD'),
                'volume': Money(trade['size'], 'BTC'),
                'timestamp': parse(trade['time']).epoch,
                'trade_id': trade['trade_id'],
            }

            trades.append(trade)

        return trades
