from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller


class BitstampBCHUSDOrderbook(OrderbookPoller):
    def __init__(self):
        self.exchange_name = u'BITSTAMP_BCH_USD'
        self.url = 'https://www.bitstamp.net/api/v2/order_book/bchusd/'
        self.poll_time = 1

    # API response format:
    # {
    #   "asks":[["0.09022887",1704.11453071]],
    #   "bids":[["0.09000011",3.74072284]],
    #   "isFrozen":"0","seq":477056211,
    # }
    def parse_order(self, order):
        return [order[0], order[1], '']

