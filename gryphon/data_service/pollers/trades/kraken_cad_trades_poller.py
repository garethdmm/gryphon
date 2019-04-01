# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.kraken_trades_poller import KrakenTrades


class KrakenCADTrades(KrakenTrades):
    def __init__(self):
        self.exchange_name = u'KRAKEN_BTC_CAD'
        self.currency = 'CAD'
        self.poll_time = 10

