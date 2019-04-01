from twisted.python import log

from gryphon.data_service.pollers.volume.volume_poller import VolumePoller


class OkcoinVolume(VolumePoller):
    def __init__(self):
        self.exchange_name = u'OKCOIN_BTC_USD'
        self.url = 'https://www.okcoin.com/api/v1/ticker.do?symbol=ltc_usd'

    def parse_volume_json(self, volume_dict):
        try:
            return volume_dict['ticker']['vol']
        except Exception as e:
            log.msg('Error getting Okcoin Volume %s' % e)
