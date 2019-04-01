from delorean import Delorean

from gryphon.data_service.auditors.orderbook_auditor import OrderbookAuditor


class BitfinexOrderbookAuditor(OrderbookAuditor):
    def __init__(self):
        super(BitfinexOrderbookAuditor, self).__init__()
        self.exchange_name = 'BITFINEX'
        self.orderbook_url = 'https://api.bitfinex.com/v1/book/btcusd'
        self.audit_time = 60

        self.acceptable_changes_threshold = 20

    def get_timestamp(self, new_orderbook):
        return Delorean().datetime
