from kraken_orderbook_poller import KrakenOrderbook


class KrakenCADOrderbook(KrakenOrderbook):
    def __init__(self):
        self.exchange_name = u'KRAKEN_BTC_CAD'
        self.currency = 'CAD'
        self.poll_time = 2
        self.orderbook_depth = 100000
