from gryphon.data_service.auditors.coinbase_orderbook_auditor import CoinbaseOrderbookAuditor


class CoinbaseCADOrderbookAuditor(CoinbaseOrderbookAuditor):
    def __init__(self):
        super(CoinbaseCADOrderbookAuditor, self).__init__()
        self.exchange_name = 'COINBASE_CAD'
        product_id = 'BTC-CAD'
        self.orderbook_url = 'https://api.exchange.coinbase.com/products/%s/book?level=3' % product_id
