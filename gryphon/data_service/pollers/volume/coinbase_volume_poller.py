from twisted.python import log

from gryphon.data_service.pollers.volume.volume_poller import VolumePoller


class CoinbaseVolume(VolumePoller):
    def __init__(self):
        self.exchange_name = u'COINBASE_BTC_USD'
        self.url = 'https://api.pro.coinbase.com/products/BTC-USD/stats'
        self.poll_time = 2

    def parse_volume_json(self, volume_dict):
        try:
            return volume_dict['volume']
        except Exception as e:
            log.msg('Error getting Coinbase Volume %s' % e)
