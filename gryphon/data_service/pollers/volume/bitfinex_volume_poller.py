from twisted.python import log

from gryphon.data_service.pollers.volume.volume_poller import VolumePoller


class BitfinexVolume(VolumePoller):
    """
    This endpoint currently has a rate limit of 30/minute.
    """

    def __init__(self):
        self.exchange_name = u'BITFINEX_BTC_USD'
        self.url = 'https://api.bitfinex.com/v1/pubticker/BTCUSD'

    def parse_volume_json(self, volume_dict):
        try:
            return volume_dict['volume']
        except Exception as e:
            log.msg('Error getting Bitfinex Volume %s' % e)
