from gryphon.data_service.pollers.volume.kraken_volume_poller import KrakenVolume


class KrakenUSDVolume(KrakenVolume):
    def __init__(self):
        self.exchange_name = u'KRAKEN_BTC_USD'
        self.currency = 'USD'
