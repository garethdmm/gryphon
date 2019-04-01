from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller


class QuadrigaOrderbook(OrderbookPoller):
    def __init__(self):
        self.exchange_name = u'QUADRIGA_BTC_CAD'
        self.url = 'https://api.quadrigacx.com/v2/order_book'
        self.poll_time = 2

    # API response format:
    # {"bids":[["302.50","1.03272000"], ...

    def parse_order(self, order):
        return [order[0], order[1], '']
