from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller


class PoloniexETHBTCOrderbook(OrderbookPoller):
    def __init__(self):
        self.exchange_name = u'POLONIEX_ETH_BTC'
        self.url = 'https://poloniex.com/public?command=returnOrderBook&currencyPair=BTC_ETH&depth=10000'  # Unclear what depth param we should be using.
        self.poll_time = 5

    # API response format:
    # {
    #   "asks":[["0.09022887",1704.11453071]],
    #   "bids":[["0.09000011",3.74072284]],
    #   "isFrozen":"0","seq":477056211,
    # }
    def parse_order(self, order):
        return [order[0], order[1], '']

