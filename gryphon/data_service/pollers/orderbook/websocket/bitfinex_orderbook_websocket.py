import json

from autobahn.twisted.websocket import connectWS, WebSocketClientFactory
from cdecimal import Decimal
from twisted.internet import defer, ssl

import gryphon.data_service.consts as consts
import gryphon.data_service.util as util
from gryphon.data_service.websocket_client import EmeraldWebSocketClientProtocol
from gryphon.data_service.pollers.orderbook.websocket.websocket_orderbook_poller import WebsocketOrderbookPoller
from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


class BitfinexOrderbookWebsocket(EmeraldWebSocketClientProtocol, WebsocketOrderbookPoller):
    def __init__(self):
        self.exchange_name = u'BITFINEX_BTC_USD'
        self.ping_interval = 5

    def connect_to_websocket(self):
        logger.info('Connecting to websocket')

        factory = WebSocketClientFactory('wss://api2.bitfinex.com:3000/ws')

        factory.protocol = type(self)

        if factory.isSecure:
            context_factor = ssl.ClientContextFactory()
        else:
            context_factor = None

        connectWS(factory, context_factor)

    def subscribe_to_websocket(self):
        logger.info('Subscribing to websocket')

        data = {
            'Event': 'subscribe',
            'Channel': 'book',
            'Pair': 'BTCUSD',
            'Prec': 'P0',
            'Len': 'FULL',  # Undocumented guess, lol.
        }

        self.sendMessage(json.dumps(data))

    # WEBSOCKET CLIENT FUNCTIONS

    @defer.inlineCallbacks
    def onOpen(self):
        logger.info('Connected to websocket')

        self.redis = yield util.setup_redis()
        binding_key = '%s.orderbook.tinker' % self.exchange_name.lower()
        self.producer = yield util.setup_producer(consts.ORDERBOOK_QUEUE, binding_key)

        # Reset everything.
        self.orderbook = {'bids': None, 'asks': None}
        self.bids_dict = {}
        self.asks_dict = {}
        self.channel_id = None
        self.have_gotten_base_orderbook = False
        self.last_amqp_push = 0

        yield self.redis.set(self.orderbook_key, None)

        self.subscribe_to_websocket()

    @defer.inlineCallbacks
    def onMessage(self, payload, isBinary):
        should_continue = yield self.check_should_continue()

        if not should_continue:
            yield self.redis.set(self.orderbook_key, None)
            return

        payload = json.loads(payload, parse_float=Decimal)

        # Initial subscription confirmation.
        if 'Event' in payload and payload['Event'] == 'subscribed':
            self.channel_id = payload['ChanId']
            return

        channel_id = payload[0]

        assert(channel_id == self.channel_id)

        # The first message after subscribing is always the base orderbook.
        if not self.have_gotten_base_orderbook:
            base_orderbook = payload[1]
            self.set_base_orderbook(base_orderbook)
            self.have_gotten_base_orderbook = True
            self.publish_orderbook()

            return

        # If we are not in one of the two initial special cases
        # then we have an orderbook change event of the format:
        # [channel_id, price, num_orders, volume_diff]
        change = payload[1:]

        self.apply_change_to_orderbook(change)
        self.publish_orderbook()

    def set_base_orderbook(self, base_orderbook):
        for order in base_orderbook:
            self.apply_change_to_orderbook(order)

    def apply_change_to_orderbook(self, change):
        # change is [0, 9, 20935.8851]
        # price, num_orders, volume
        # volume is + for bids, - for asks
        price = change[0]
        volume = change[2]

        if volume > 0:
            self.bids_dict[price] = volume
        elif volume < 0:
            self.asks_dict[price] = abs(volume)
        else:
            # When volume is 0 we don't know if this is for bids or asks we can safely
            # remove both, since there will never be a bid and an ask at the same price.
            self.bids_dict[price] = 0
            self.asks_dict[price] = 0

    def get_orderbook_to_publish(self):
        # We store the orderbook internally as a bid and ask dict, so we convert it here
        # to sorted lists of [price, volume] orders.
        bids = []
        asks = []

        for price, volume in sorted(self.bids_dict.iteritems(), reverse=True):
            if volume > 0:
                bids.append([str(price), str(volume), ''])

        for price, volume in sorted(self.asks_dict.iteritems()):
            if volume > 0:
                asks.append([str(price), str(volume), ''])

        orderbook = {}
        orderbook['bids'] = bids
        orderbook['asks'] = asks

        return orderbook

    def print_orderbook(self):
        """Print current orderbook in format similar to Bitfinex's homepage orderbook"""
        bids = self.orderbook['bids']
        asks = self.orderbook['asks']

        if not bids or not asks:
            return

        # Pushes orderbook to bottom of terminal for a live-updating effect.
        logger.info("\n" * 100)
        logger.info('{:=^78}'.format(' ORDER BOOK '))
        logger.info('{: ^39}{: ^39}'.format('BIDS', 'ASKS'))

        titles = "{:^7} | {:^12} | {:^12} ||| {:^12} | {:^12} | {:^7}".format(
            'Price',
            'Amount',
            'Cumulative',
            'Cumulative',
            'Amount',
            'Price',
        )

        logger.info(titles)

        bid_sum = 0
        ask_sum = 0

        while bids and asks:
            bid = bids.pop(0)
            ask = asks.pop(0)

            bid_sum += bid[1]
            ask_sum += ask[1]

            line = "{:^7.1f} | {:^12.1f} | {:^12.1f} ||| {:^12.1f} | {:^12.1f} | {:^7.1f}".format(
                bid[0],
                bid[1],
                bid_sum,
                ask_sum,
                ask[1],
                ask[0]
            )

            logger.info(line)
