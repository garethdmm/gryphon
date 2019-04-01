from twisted.python import log

from gryphon.data_service.pollers.volume.volume_poller import VolumePoller


class QuadrigaVolume(VolumePoller):
    def __init__(self):
        self.exchange_name = u'QUADRIGA_BTC_CAD'
        self.url = 'https://api.quadrigacx.com/v2/ticker?book=btc_cad'

    def parse_volume_json(self, volume_dict):
        try:
            return volume_dict['volume']
        except Exception as e:
            log.msg('Error getting Quadriga Volume %s' % e)
