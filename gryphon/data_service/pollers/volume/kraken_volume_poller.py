from twisted.python import log

from gryphon.data_service.pollers.volume.volume_poller import VolumePoller
from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange


class KrakenVolume(VolumePoller):
    def __init__(self):
        self.exchange_name = u'KRAKEN_BTC_EUR'
        self.currency = 'EUR'

    @property
    def pair(self):
        return KrakenBTCEURExchange.construct_pair(self.currency)

    @property
    def url(self):
        return 'https://api.kraken.com/0/public/Ticker?pair=%s' % self.pair

    def parse_volume_json(self, volume_dict):
        try:
            return volume_dict['result'][self.pair]['v'][1]
        except Exception as e:
            log.msg('Error getting Kraken Volume %s' % e)
