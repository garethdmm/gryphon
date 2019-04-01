# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.orderbook.bitfinex_orderbook_poller import BitfinexOrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_bch_btc_orderbook_poller import BitstampBCHBTCOrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_bch_btc_orderbook_poller import BitstampBCHBTCOrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_bch_eur_orderbook_poller import BitstampBCHEUROrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_bch_usd_orderbook_poller import BitstampBCHUSDOrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_btc_eur_orderbook_poller import BitstampBTCEUROrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_eth_btc_orderbook_poller import BitstampETHBTCOrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_eth_eur_orderbook_poller import BitstampETHEUROrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_eth_usd_orderbook_poller import BitstampETHUSDOrderbook
from gryphon.data_service.pollers.orderbook.bitstamp_btc_usd_orderbook_poller import BitstampBTCUSDOrderbook
from gryphon.data_service.pollers.orderbook.gemini_eth_btc_orderbook_poller import GeminiETHBTCOrderbook
from gryphon.data_service.pollers.orderbook.gemini_eth_usd_orderbook_poller import GeminiETHUSDOrderbook
from gryphon.data_service.pollers.orderbook.gemini_orderbook_poller import GeminiOrderbook
from gryphon.data_service.pollers.orderbook.itbit_orderbook_poller import ItbitOrderbook
from gryphon.data_service.pollers.orderbook.kraken_cad_orderbook_poller import KrakenCADOrderbook
from gryphon.data_service.pollers.orderbook.kraken_orderbook_poller import KrakenOrderbook
from gryphon.data_service.pollers.orderbook.kraken_usd_orderbook_poller import KrakenUSDOrderbook
from gryphon.data_service.pollers.orderbook.okcoin_orderbook_poller import OkCoinOrderbook
from gryphon.data_service.pollers.orderbook.poloniex_eth_btc_orderbook_poller import PoloniexETHBTCOrderbook
from gryphon.data_service.pollers.orderbook.quadriga_orderbook_poller import QuadrigaOrderbook
from gryphon.data_service.pollers.orderbook.websocket.coinbase_cad_orderbook_websocket import CoinbaseCADOrderbookWebsocket
from gryphon.data_service.pollers.orderbook.coinbase_btc_usd_orderbook_poller import CoinbaseBTCUSDOrderbook
from gryphon.data_service.task import Task


class OrderbookPollTask(Task):
    def __init__(self, exchanges=[]):
        exchange_pollers = {
            'BITFINEX_BTC_USD': BitfinexOrderbook(),
            'BITSTAMP_BCH_EUR': BitstampBCHEUROrderbook(),
            'BITSTAMP_BCH_USD': BitstampBCHUSDOrderbook(),
            'BITSTAMP_BCH_BTC': BitstampBCHBTCOrderbook(),
            'BITSTAMP_BTC_EUR': BitstampBTCEUROrderbook(),
            'BITSTAMP_BTC_USD': BitstampBTCUSDOrderbook(),
            'BITSTAMP_ETH_BTC': BitstampETHBTCOrderbook(),
            'BITSTAMP_ETH_EUR': BitstampETHEUROrderbook(),
            'BITSTAMP_ETH_USD': BitstampETHUSDOrderbook(),
            'COINBASE_BTC_USD': CoinbaseBTCUSDOrderbook(),
            'GEMINI_BTC_USD': GeminiOrderbook(),
            'GEMINI_ETH_BTC': GeminiETHBTCOrderbook(),
            'GEMINI_ETH_USD': GeminiETHUSDOrderbook(),
            'ITBIT_BTC_USD': ItbitOrderbook(),
            'KRAKEN_BTC_EUR': KrakenOrderbook(),
            'KRAKEN_BTC_USD': KrakenUSDOrderbook(),
            'KRAKEN_BTC_CAD': KrakenCADOrderbook(),
            'OKCOIN_BTC_USD': OkCoinOrderbook(),
            'POLONIEX_ETH_BTC': PoloniexETHBTCOrderbook(),
        }

        if exchanges:
            self.pollers = [
                exchange_pollers[ex]
                for ex in exchanges
                if ex in exchange_pollers
            ]
        else:
            self.pollers = exchange_pollers.values()

    def start_task(self):
        for poller in self.pollers:
            poller.start()
