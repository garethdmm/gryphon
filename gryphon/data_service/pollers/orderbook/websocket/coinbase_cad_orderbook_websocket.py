from gryphon.data_service.pollers.orderbook.websocket.coinbase_orderbook_websocket import CoinbaseOrderbookWebsocket


class CoinbaseCADOrderbookWebsocket(CoinbaseOrderbookWebsocket):

    def __init__(self):
        super(CoinbaseCADOrderbookWebsocket, self).__init__()
        self.exchange_name = u'COINBASE_BTC_CAD'
        self.product_id = 'BTC-CAD'
