from kraken_orderbook_poller import KrakenOrderbook


class KrakenUSDOrderbook(KrakenOrderbook):
    def __init__(self):
        self.exchange_name = u'KRAKEN_BTC_USD'
        self.currency = 'USD'
        self.poll_time = 2
        self.orderbook_depth = 100000
