# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.trades.bitfinex_trades_poller import BitfinexTrades
from gryphon.data_service.pollers.trades.bitstamp_trades_poller import BitstampTrades
from gryphon.data_service.pollers.trades.coinbase_cad_trades_poller import CoinbaseCadTrades
from gryphon.data_service.pollers.trades.coinbase_trades_poller import CoinbaseTrades
from gryphon.data_service.pollers.trades.gemini_trades_poller import GeminiTrades
from gryphon.data_service.pollers.trades.itbit_trades_poller import ItbitTrades
from gryphon.data_service.pollers.trades.kraken_cad_trades_poller import KrakenCADTrades
from gryphon.data_service.pollers.trades.kraken_trades_poller import KrakenTrades
from gryphon.data_service.pollers.trades.kraken_usd_trades_poller import KrakenUSDTrades
from gryphon.data_service.pollers.trades.okcoin_trades_poller import OkcoinTrades
from gryphon.data_service.pollers.trades.quadriga_trades_poller import QuadrigaTrades
from gryphon.data_service.task import Task


class TradesPollTask(Task):
    def __init__(self, exchanges=[]):
        exchange_pollers = {
            'KRAKEN': KrakenTrades(),
            'KRAKEN_USD': KrakenUSDTrades(),
            'KRAKEN_CAD': KrakenCADTrades(),
            'ITBIT': ItbitTrades(),
            'QUADRIGA': QuadrigaTrades(),
            'OKCOIN': OkcoinTrades(),
            'GEMINI': GeminiTrades(),
            'BITFINEX': BitfinexTrades(),
            'COINBASE_BTC_USD': CoinbaseTrades(),
            'BITSTAMP_BTC_USD': BitstampTrades(),
            'COINBASE_CAD': CoinbaseCadTrades(),
        }

        if exchanges:
            self.pollers = [exchange_pollers[ex] for ex in exchanges]
        else:
            self.pollers = exchange_pollers.values()

    def start_task(self):
        for poller in self.pollers:
            poller.start()
