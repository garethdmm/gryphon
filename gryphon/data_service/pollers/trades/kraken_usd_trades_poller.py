# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.kraken_trades_poller import KrakenTrades


class KrakenUSDTrades(KrakenTrades):
    def __init__(self):
        self.exchange_name = u'KRAKEN_BTC_USD'
        self.currency = 'USD'
        self.poll_time = 10
