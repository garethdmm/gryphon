# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.trades_poller import TradesPoller
from gryphon.lib.money import Money


class QuadrigaTrades(TradesPoller):
    def __init__(self):
        self.exchange_name = u'QUADRIGA_BTC_CAD'
        self.url = 'https://api.quadrigacx.com/public/trades?book=btc_cad'
        self.poll_time = 10

    def parse_trades(self, resp_obj):
        trades = []

        for trade in resp_obj:
            # No unique id comes back with the trade so we use the milliseconds
            # timestamp.
            trade = {
                'exchange': self.exchange_name,
                'price': Money(trade['rate'], 'CAD'),
                'volume': Money(trade['amount'], 'BTC'),
                'timestamp': int(trade['datetime']) / 1000.0,
                'trade_id': int(trade['datetime']),
            }

            trades.append(trade)

        return trades
