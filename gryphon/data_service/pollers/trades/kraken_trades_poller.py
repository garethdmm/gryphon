# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.trades_poller import TradesPoller
from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
from gryphon.lib.money import Money


class KrakenTrades(TradesPoller):
    def __init__(self):
        self.exchange_name = u'KRAKEN_BTC_EUR'
        self.currency = 'EUR'
        self.poll_time = 10

    @property
    def pair(self):
        return KrakenBTCEURExchange.construct_pair(self.currency)

    @property
    def url(self):
        return 'https://api.kraken.com/0/public/Trades?pair=%s' % self.pair

    def parse_trades(self, resp_obj):
        trades = []

        for trade in resp_obj['result'][self.pair]:
            trade = {
                'exchange': self.exchange_name,
                'price': Money(trade[0], self.currency),
                'volume': Money(trade[1], 'BTC'),
                'timestamp': trade[2],
                'trade_id': int(trade[2] * 10000),
            }

            trades.append(trade)

        return trades
