from delorean import Delorean

from gryphon.data_service.auditors.orderbook_auditor import OrderbookAuditor


class CoinbaseOrderbookAuditor(OrderbookAuditor):
    def __init__(self):
        super(CoinbaseOrderbookAuditor, self).__init__()
        self.exchange_name = 'COINBASE_BTC_USD'
        product_id = 'BTC-USD'
        self.orderbook_url = 'https://api.pro.coinbase.com/products/%s/book?level=3' % product_id
        self.audit_time = 60

        self.acceptable_changes_threshold = 40

    def get_timestamp(self, new_orderbook):
        return Delorean().datetime
