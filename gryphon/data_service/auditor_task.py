# -*- coding: utf-8 -*-
from gryphon.data_service.auditors.bitstamp_orderbook_auditor import BitstampOrderbookAuditor
from gryphon.data_service.auditors.coinbase_cad_orderbook_auditor import CoinbaseCADOrderbookAuditor
from gryphon.data_service.auditors.coinbase_orderbook_auditor import CoinbaseOrderbookAuditor
from gryphon.data_service.auditors.heartbeat_auditor import HeartbeatAuditor
from gryphon.data_service.auditors.performance_auditor import PerformanceAuditor
from gryphon.data_service.auditors.trades_auditor import TradesAuditor
from gryphon.data_service.task import Task


class AuditorTask(Task):
    def __init__(self, exchanges=[]):
        exchange_orderbook_auditors = {
            'COINBASE_BTC_USD': CoinbaseOrderbookAuditor(),
            'BITSTAMP_BTC_USD': BitstampOrderbookAuditor(),
            'COINBASE_BTC_CAD': CoinbaseCADOrderbookAuditor(),
        }

        if exchanges:
            self.auditors = [
                exchange_orderbook_auditors[ex]
                for ex in exchanges
                if ex in exchange_orderbook_auditors
            ]

        else:
            self.auditors = exchange_orderbook_auditors.values()

        self.auditors.extend([
            HeartbeatAuditor(),
            PerformanceAuditor(),
            TradesAuditor(exchanges=exchanges)
        ])

    def start_task(self):
        for auditor in self.auditors:
            auditor.start()

