from collections import defaultdict
import json

from autobahn.twisted.websocket import connectWS, WebSocketClientFactory
from cdecimal import Decimal
from twisted.internet import defer, reactor, ssl

import gryphon.data_service.consts as consts
import gryphon.data_service.util as util
from gryphon.data_service.websocket_client import EmeraldWebSocketClientProtocol
from gryphon.data_service.pollers.orderbook.websocket.websocket_orderbook_poller import WebsocketOrderbookPoller
from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


class CoinbaseOrderbookWebsocket(EmeraldWebSocketClientProtocol, WebsocketOrderbookPoller):
    def __init__(self):
        self.exchange_name = u'COINBASE_BTC_USD'
        self.product_id = 'BTC-USD'
        self.base_url = 'https://api.exchange.coinbase.com/products/%s/book?level=3'
        self.url = self.base_url % self.product_id
        self.ping_interval = 5

    def connect_to_websocket(self):
        logger.info('Connecting to websocket')

        factory = WebSocketClientFactory(
            'wss://ws-feed.exchange.coinbase.com',
            debug=False,
        )

        # This actually creates a new Instance of CoinbaseOrderbook.
        factory.protocol = type(self)

        if factory.isSecure:
            context_factor = ssl.ClientContextFactory()
        else:
            context_factor = None

        connectWS(factory, context_factor)

    def subscribe_to_websocket(self):
        logger.info('Subscribing to websocket')

        data = {
            'type': 'subscribe',
            'product_id': self.product_id,
        }

        self.sendMessage(json.dumps(data))

    # REQUEST POLLER FUNCTIONS

    def parse_response(self, resp_obj):
        """
        This function will parse the base orderbook from the http endpoint.

        {"timestamp": "1412095328", "bids": [["382.74", "4.85241530"],
        """
        logger.info('Fetching Base Orderbook')

        self.orderbook_sequence_number = resp_obj['sequence']

        if (self.orderbook_sequence_number > self.first_sequence_number
                and self.first_sequence_number != 0):

            self.orderbook = {
                'bids': self.parse_orders(resp_obj['bids']),
                'asks': self.parse_orders(resp_obj['asks'])
            }

            logger.info(
                'Established Orderbook, Sequence: %s' % self.orderbook_sequence_number,
            )
        else:
            # Get the orderbook again since it was too old.
            logger.debug('Orderbook is too out-of-date. Retrying')

            reactor.callLater(1, self.get_request)

    # WEBSOCKET CLIENT FUNCTIONS

    @defer.inlineCallbacks
    def onOpen(self):
        logger.info('Connected to websocket')

        reactor.callLater(self.ping_interval, self.keepalive)

        self.redis = yield util.setup_redis()
        binding_key = '%s.orderbook.tinker' % self.exchange_name.lower()
        self.producer = yield util.setup_producer(consts.ORDERBOOK_QUEUE, binding_key)

        # Reset everything.
        self.orderbook = ''
        self.orderbook_change_backlog = {}
        self.first_sequence_number = 0
        self.current_sequence_number = 0
        self.orderbook_sequence_number = 0
        self.received_orders = {}
        self.last_amqp_push = 0
        yield self.redis.set(self.orderbook_key, None)

        # Start fetching the base orderbook from self.url. The request poller will call
        # parse_response with the response.
        self.get_request()

        self.subscribe_to_websocket()

    def keepalive(self):
        """
        Sends a keepalive ping to the Coinbase Websocket every 5 seconds. 5s is chosen
        so that we avoid the 10s "Cached orderbook too old" errors on gryphon-fury.
        Without any ping, the connection gets closed after 60 seconds of no messages.
        """
        logger.debug('Ping')
        self.sendPing('keepalive')

        reactor.callLater(self.ping_interval, self.keepalive)

    def onPong(self, payload):
        """
        Catch the pong back from Coinbase, and know that we are still successfully
        connected.
        """
        # We had one day where the Coinbase fundamental value did not change all day.
        # We think this may have been caused by them Ponging our Pings, but not
        # actually sending any data. Since Coinbase is so critical to our system, we
        # are only re-publishing orderbooks when there is an actual update (not just a
        # pong).
        logger.debug("Pong")

    @defer.inlineCallbacks
    def onMessage(self, payload, isBinary):
        should_continue = yield self.check_should_continue()

        if not should_continue:
            yield self.redis.set(self.orderbook_key, None)
            return

        payload = json.loads(payload)

        # Deal with sequence numbers.
        sequence_number = payload['sequence']
        if not self.first_sequence_number:
            self.first_sequence_number = sequence_number

        if (sequence_number == (1 + self.current_sequence_number) or
                sequence_number == self.first_sequence_number):
            # Keep going - sequence number is good.
            self.current_sequence_number = sequence_number
        else:
            # Sequence number is bad restart.
            logger.info('Sequencing Numbers on Coinbase came in wrong. Restarting.')

            yield self.restart()

        if payload['type'] in ['received', 'done', 'change', 'open']:
            if self.orderbook and not self.orderbook_change_backlog:
                # NO Backlog of changes. apply the change.
                self.apply_change_to_orderbook(payload)

                if payload['type'] != 'received':
                    self.publish_orderbook()

                return
            elif self.orderbook and self.orderbook_change_backlog:
                logger.info('Working down the backlog')

                # Adding current update to backlog.
                self.orderbook_change_backlog[sequence_number] = payload

                self.apply_backlog()

                if payload['type'] != 'received':
                    self.publish_orderbook()

                return
            else:
                logger.debug('Base Orderbook Not Ready')
                self.orderbook_change_backlog[payload['sequence']] = payload

                return
        else:
            # Match orders.
            pass

    # HELPER FUNCTIONS

    def apply_backlog(self):
        orderbook_backlog_sequence_numbers = sorted(
            self.orderbook_change_backlog.keys(),
        )

        num_changes = len(orderbook_backlog_sequence_numbers)
        logger.info('Applying %s changes to Orderbook' % num_changes)

        for seq_num in orderbook_backlog_sequence_numbers:
            if seq_num > self.orderbook_sequence_number:
                self.apply_change_to_orderbook(
                    self.orderbook_change_backlog.pop(seq_num),
                )
            else:
                # this update is too old. get rid of it
                self.orderbook_change_backlog.pop(seq_num)

    def apply_change_to_orderbook(self, change):
        """
        {
              "type": "received",
              "sequence": 10,
              "order_id": "<order id>",
              "size": "0.00",
              "price": "0.00",
              "side": "buy"
        }
        {
              "type": "open",
              "sequence": 10,
              "order_id": "d50ec984-77a8-460a-b958-66f114b0de9b",
              "price": "200.2",
              "remaining_size": "1.00"
        }

        {
              "type": "done",
              "sequence": 10,
              "price": "200.2",
              "order_id": "d50ec984-77a8-460a-b958-66f114b0de9b",
              "reason": "filled" // canceled
        }

        {
              "type": "change",
              "sequence": 80,
              "order_id": "ac928c66-ca53-498f-9c13-a110027a60e8",
              "time": "2014-11-07T08:19:27.028459Z",
              "new_size": "5.23512",
              "old_size": "12.234412",
              "price": "400.23"
        }
        """

        side = 'bids' if change['side'] == 'buy' else 'asks'

        if change['type'] == 'received':
            # add to orderbook to the received orders.
            self.received_orders[change['order_id']] = change

        elif change['type'] == 'open':
            # Grab the order from the received orders, create a new order in the
            # orderbook.
            received_order = self.received_orders[change['order_id']]
            self.received_orders.pop(change['order_id'])

            change.update(received_order)

            self.orderbook[side][change['order_id']] = {
                'price': change['price'],
                'volume': change['remaining_size'],
            }

        elif change['type'] == 'done':
            if change['order_id'] in self.orderbook[side]:
                self.orderbook[side].pop(change['order_id'])
            else:
                # An order was closed before it hit the orderbook - match.
                pass

        elif change['type'] == 'change':
            if change['order_id'] in self.orderbook[side]:
                self.orderbook[side][change['order_id']]['volume'] = change['new_size']
            elif change['order_id'] in self.received_orders:
                self.received_orders[change['order_id']]['volume'] = change['new_size']
            else:
                logger.info(
                    'Coinbase - change message order not in orderbook or received orders',
                )

        else:
            pass

    def get_order_from_orderbook(self, order_id):
        if order_id in self.orderbook['bids']:
            return self.orderbook['bids'][order_id]
        elif order_id in self.orderbook['asks']:
            return self.orderbook['asks'][order_id]
        else:
            return None

    def parse_orders(self, orders):
        """Returns a price keyed orders"""
        orders_dict = {}

        for order in orders:
            orders_dict[order[2]] = {'price': order[0], 'volume': order[1]}

        return orders_dict

    def get_orderbook_to_publish(self):
        orderbook = self.orderbook
        fancy_orderbook = {'bids': defaultdict(Decimal), 'asks': defaultdict(Decimal)}

        for bid in orderbook['bids']:
            fancy_orderbook['bids'][[bid]['price']] += Decimal(bid['volume'])

        for ask in orderbook['asks']:
            fancy_orderbook['asks'][ask['price']] += Decimal(ask['volume'])

        sorted_bid_keys = sorted(
            fancy_orderbook['bids'].keys(),
            key=lambda (k): float(k),
            reverse=True,
        )

        sorted_ask_keys = sorted(
            fancy_orderbook['asks'].keys(),
            key=lambda (k): float(k),
        )

        bids = [[k, str(fancy_orderbook['bids'][k]), ''] for k in sorted_bid_keys]

        asks = [[k, str(fancy_orderbook['asks'][k]), ''] for k in sorted_ask_keys]

        return {
            'bids': bids,
            'asks': asks,
        }

