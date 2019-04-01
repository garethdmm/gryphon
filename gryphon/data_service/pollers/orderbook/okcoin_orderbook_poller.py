from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller


class OkCoinOrderbook(OrderbookPoller):
    def __init__(self):
        self.exchange_name = u'OKCOIN_BTC_USD'
        self.url = 'https://www.okcoin.com/api/v1/depth.do?merge=0&symbol=btc_usd'
        self.poll_time = 2

    # API response format:
    # {"bids":[[787.1, 0.35], ...

    def parse_order(self, order):
        return [order[0], order[1], '']
