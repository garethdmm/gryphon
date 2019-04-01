from twisted.python import log

from gryphon.data_service.pollers.volume.volume_poller import VolumePoller


class ItbitVolume(VolumePoller):
    def __init__(self):
        self.exchange_name = u'ITBIT_BTC_USD'
        self.url = 'https://api.itbit.com/v1/markets/XBTUSD/ticker'

    def parse_volume_json(self, volume_dict):
        try:
            return volume_dict['volume24h']
        except Exception as e:
            log.msg('Error getting Itbit Volume %s' % e)
