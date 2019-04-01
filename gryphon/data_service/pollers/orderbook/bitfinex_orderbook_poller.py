from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller


class BitfinexOrderbook(OrderbookPoller):
    """
    2018/01/17 This endpoint currently has a 60/minute rate limit.
    """

    def __init__(self):
        self.exchange_name = u'BITFINEX_BTC_USD'
        self.poll_time = 3
        self.orderbook_depth = 50000
        self.url = 'https://api.bitfinex.com/v1/book/btcusd?limit_bids=%s&limit_asks=%s' % (self.orderbook_depth, self.orderbook_depth)

    def parse_order(self, order):
        """
        API response format:
        {"bids":[{"price":"405.02","amount":"0.001","timestamp":"1411774902.0"}, ...
        """
        return [order['price'], order['amount'], order['timestamp']]
