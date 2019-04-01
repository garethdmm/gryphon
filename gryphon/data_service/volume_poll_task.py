# -*- coding: utf-8 -*-
from gryphon.data_service.pollers.volume.bitfinex_volume_poller import BitfinexVolume
from gryphon.data_service.pollers.volume.bitstamp_volume_poller import BitstampVolume
from gryphon.data_service.pollers.volume.coinbase_cad_volume_poller import CoinbaseCADVolume
from gryphon.data_service.pollers.volume.coinbase_volume_poller import CoinbaseVolume
from gryphon.data_service.pollers.volume.itbit_volume_poller import ItbitVolume
from gryphon.data_service.pollers.volume.kraken_cad_volume_poller import KrakenCADVolume
from gryphon.data_service.pollers.volume.kraken_usd_volume_poller import KrakenUSDVolume
from gryphon.data_service.pollers.volume.kraken_volume_poller import KrakenVolume
from gryphon.data_service.pollers.volume.okcoin_volume_poller import OkcoinVolume
from gryphon.data_service.pollers.volume.quadriga_volume_poller import QuadrigaVolume
from gryphon.data_service.task import Task


class VolumePollTask(Task):
    def __init__(self, exchanges=[]):
        exchange_pollers = {
            'KRAKEN': KrakenVolume(),
            'KRAKEN_USD': KrakenUSDVolume(),
            'KRAKEN_CAD': KrakenCADVolume(),
            'ITBIT': ItbitVolume(),
            'QUADRIGA': QuadrigaVolume(),
            'OKCOIN': OkcoinVolume(),
            'BITFINEX': BitfinexVolume(),
            'COINBASE_BTC_USD': CoinbaseVolume(),
            'BITSTAMP_BTC_USD': BitstampVolume(),
            'COINBASE_CAD': CoinbaseCADVolume(),
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
