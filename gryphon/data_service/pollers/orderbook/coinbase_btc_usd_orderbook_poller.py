from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller


class CoinbaseBTCUSDOrderbook(OrderbookPoller):
    def __init__(self):
        self.exchange_name = u'COINBASE_BTC_USD'
        self.product_id = 'BTC-USD'
        self.base_url = 'https://api.pro.coinbase.com/products/%s/book?level=3'
        self.url = self.base_url % self.product_id
        self.poll_time = 2

    def parse_order(self, order):
        return [order[0], order[1], '']

