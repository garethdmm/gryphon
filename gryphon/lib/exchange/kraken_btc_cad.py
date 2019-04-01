from cdecimal import Decimal

from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange
from gryphon.lib.logger import get_logger
from gryphon.lib.money import Money

logger = get_logger(__name__)


class KrakenBTCCADExchange(KrakenBTCEURExchange):
    def __init__(self, session=None, configuration=None):
        super(KrakenBTCCADExchange, self).__init__(session)

        self.name = u'KRAKEN_BTC_CAD'
        self.friendly_name = u'Kraken BTC-CAD'
        self.currency = 'CAD'
        self.price_decimal_precision = 1 # As of Feb 2018

        # Updated by Gareth on 2016-9-20
        self.market_order_fee = Decimal('0.0026')
        self.limit_order_fee = Decimal('0.0016')
        self.fee = self.market_order_fee
        self.fiat_balance_tolerance = Money('0.0001', 'CAD')
        self.volume_balance_tolerance = Money('0.00000001', 'BTC')
        self.min_order_size = Money('0.002', 'BTC')
        self.max_tick_speed = 5
        self.use_cached_orderbook = False

        if configuration:
            self.configure(configuration)

    def load_creds(self):
        try:
            self.api_key
            self.secret
        except AttributeError:
            self.api_key = self._load_env('KRAKEN_BTC_CAD_API_KEY')
            self.secret = self._load_env('KRAKEN_BTC_CAD_API_SECRET')
