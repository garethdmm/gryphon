from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller
from gryphon.lib.exchange.kraken_btc_eur import KrakenBTCEURExchange


class KrakenOrderbook(OrderbookPoller):
    def __init__(self):
        self.exchange_name = u'KRAKEN_BTC_EUR'
        self.currency = 'EUR'
        self.poll_time = 2
        # How many orders to get. Kraken appears to have a limit of 500 right now,
        # but this number is future-proofed.
        self.orderbook_depth = 100000

    @property
    def pair(self):
        return KrakenBTCEURExchange.construct_pair(self.currency)

    @property
    def url(self):
        return 'https://api.kraken.com/0/public/Depth?pair=%s&count=%s' % (
            self.pair,
            self.orderbook_depth,
        )

    # API response format:
    # {"result":{"XXBTZEUR":{"bids":[["202.33000","6.658",1442880257], ...

    def get_bids_and_asks(self, response):
        orderbook = response['result'][self.pair]
        raw_bids = orderbook['bids']
        raw_asks = orderbook['asks']
        return raw_bids, raw_asks

    def parse_order(self, order):
        return [order[0], order[1], order[2]]
