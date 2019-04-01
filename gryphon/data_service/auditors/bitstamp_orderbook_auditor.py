from delorean import epoch

from gryphon.data_service.auditors.orderbook_auditor import OrderbookAuditor


class BitstampOrderbookAuditor(OrderbookAuditor):
    def __init__(self):
        super(BitstampOrderbookAuditor, self).__init__()
        self.exchange_name = 'BITSTAMP_BTC_USD'
        self.orderbook_url = 'https://www.bitstamp.net/api/order_book/'

        self.acceptable_changes_threshold = 40

    def get_timestamp(self, new_orderbook):
        return epoch(float(new_orderbook['timestamp'])).datetime
