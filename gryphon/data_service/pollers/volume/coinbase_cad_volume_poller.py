from twisted.python import log

from gryphon.data_service.pollers.volume.volume_poller import VolumePoller


class CoinbaseCADVolume(VolumePoller):
    def __init__(self):
        self.exchange_name = u'COINBASE_BTC_CAD'
        self.url = 'https://api.exchange.coinbase.com/products/BTC-CAD/stats'

    def parse_volume_json(self, volume_dict):
        """
        Parses this:
        {
            "open":"377.99000000",
            "high":"382.25000000",
            "low":"351.16000000",
            "volume":"11457.39541978"
        }
        """

        try:
            return volume_dict['volume']
        except Exception as e:
            log.msg('Error getting Coinbase CAD Volume %s' % e)
