from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller


class GeminiETHBTCOrderbook(OrderbookPoller):
    def __init__(self):
        self.exchange_name = u'GEMINI_ETH_BTC'
        self.url = 'https://api.gemini.com/v1/book/ETHBTC?limit_bids=0&limit_asks=0'
        self.poll_time = 5  # Unclear what this should be.

    # API response format:
    # {"bids":[{"price":"405.02","amount":"0.001","timestamp":"1411774902.0"}, ...

    def parse_order(self, order):
        return [order['price'], order['amount'], order['timestamp']]
