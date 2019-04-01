from bitstamp import BitstampBTCUSDExchange
import os
import json
from cdecimal import *
from gryphon.lib.logger import get_logger
logger = get_logger(__name__)


class BitstampStagingExchange(BitstampBTCUSDExchange):
    def __init__(self, session=None, use_cached_orderbook=False):
        super(BitstampStagingExchange, self).__init__(session)
        self.name = u'BITSTAMP_STAGING'
        self.friendly_name = u'BitstampStaging'
        self.currency = u'USD'
        self.fee = Decimal("0.0020")
        self._order_book = None
        self.use_cached_orderbook = use_cached_orderbook

    def load_creds(self):
        try:
            self.api_key
            self.secret
            self.client_id
        except AttributeError:
            self.api_key = self.load_env('BITSTAMP_STAGING_API_KEY')
            self.secret = self.load_env('BITSTAMP_STAGING_API_SECRET')
            self.client_id = self.load_env('BITSTAMP_STAGING_CLIENT_ID')
