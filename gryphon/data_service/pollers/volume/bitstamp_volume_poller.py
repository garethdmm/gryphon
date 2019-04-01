from twisted.python import log

from gryphon.data_service.pollers.volume.volume_poller import VolumePoller


class BitstampVolume(VolumePoller):
    def __init__(self):
        self.exchange_name = u'BITSTAMP_BTC_USD'
        self.url = 'https://priv-api.bitstamp.net/api/ticker/'

    def parse_volume_json(self, volume_dict):
        try:
            return volume_dict['volume']
        except Exception as e:
            log.msg('Error getting Bitstamp Volume %s' % e)
