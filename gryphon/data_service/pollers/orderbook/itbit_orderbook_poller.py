from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller


class ItbitOrderbook(OrderbookPoller):
    def __init__(self):
        self.exchange_name = u'ITBIT_BTC_USD'
        self.url = 'https://api.itbit.com/v1/markets/XBTUSD/order_book'
        self.poll_time = 2

    # API response format:
    # {"bids":[["373.51","1.6463"], ...

    def parse_order(self, order):
        return [order[0], order[1], '']
