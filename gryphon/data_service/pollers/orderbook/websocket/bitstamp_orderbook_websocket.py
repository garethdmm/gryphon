from collections import OrderedDict
import json

from autobahn.twisted.websocket import WebSocketClientFactory
from delorean import Delorean
import treq
from twisted.internet import defer, reactor
from twisted.python import log

import gryphon.data_service.consts as consts
import gryphon.data_service.util as util
from gryphon.data_service.websocket_client import EmeraldWebSocketClientProtocol
from gryphon.data_service.pollers.orderbook.websocket.websocket_orderbook_poller import WebsocketOrderbookPoller
from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


class BitstampOrderbookWebsocket(EmeraldWebSocketClientProtocol, WebsocketOrderbookPoller):
    def __init__(self):
        self.exchange_name = u'BITSTAMP_BTC_USD'

    def connect_to_websocket(self):
        logger.info('Connecting to websocket')

        factory = WebSocketClientFactory(
            'ws://ws.pusherapp.com:80/app/de504dc5763aeef9ff52?protocol=6',
            debug=False,
        )

        # This actually creates a new Instance of BitstampOrderbook.
        factory.protocol = type(self)
        reactor.connectTCP("ws.pusherapp.com", 80, factory)

    def subscribe_to_websocket(self):
        logger.info('Subscribing to websocket')

        data = {
            'channel': 'diff_order_book',
        }

        event = {
            'event': 'pusher:subscribe',
            'data': data,
        }

        self.sendMessage(json.dumps(event))

    # REQUEST POLLER FUNCTIONS

    def get_response(self, response):
        """
        Reimplemented this and handle_response_error from the RequestPoller base class
        because we need to be able to recover from errors that occur in the setup
        process for a websocket poller.  Previously an error in the initial REST call
        would prevent the poller from initializing properly.
        """

        # Parse the Response and check for errors
        d = treq.content(response)

        # We want to add parse_float=Decimal, but it currently breaks json writing
        # in later code paths
        d.addCallback(json.loads)
        d.addCallback(self.parse_response)
        d.addErrback(self.handle_response_error, response)

        return d

    def handle_response_error(self, error_text, response, *args, **kwargs):
        d = treq.text_content(response).addCallback(
            self.log_response,
            u'Error in Response from URL:%s %s' % (self.url, error_text),
            log.err,
        )

        d.addCallback(self.retry_request)

    def retry_request(self, *args):
        log.msg('Retrying initial orderbook call - Looking for Orderbook Timestamp (%s) to be greater than First Change Timestamp (%s)' % (self.orderbook_timestamp, self.first_change_timestamp))

        reactor.callLater(0.5, self.get_request)

    def parse_response(self, resp_obj):
        """
        This function will collect the baseline orderbook from the http endpoint.

        {"timestamp": "1412095328", "bids": [["382.74", "4.85241530"],
        """
        self.orderbook_timestamp = int(resp_obj['timestamp'])

        if (self.orderbook_timestamp > self.first_change_timestamp
                and self.message_count > self.message_count_buffer):
            self.orderbook = {
                'bids': self.parse_orders(resp_obj['bids']),
                'asks': self.parse_orders(resp_obj['asks']),
            }
        else:
            # Get the orderbook again since it was too old.
            self.retry_request()

    # WEBSOCKET CLIENT FUNCTIONS
    @defer.inlineCallbacks
    def onOpen(self):
        logger.info('Connected to websocket')

        self.url = 'https://priv-api.bitstamp.net/api/order_book/'
        self.redis = yield util.setup_redis()

        binding_key = '%s.orderbook.tinker' % self.exchange_name.lower()
        self.producer = yield util.setup_producer(consts.ORDERBOOK_QUEUE, binding_key)

        # Reset everything
        self.orderbook = ''
        self.orderbook_timestamp = None
        self.orderbook_change_backlog = {}
        self.first_change_timestamp = None
        self.message_count = 0
        self.message_count_buffer = 3
        self.last_amqp_push = 0

        yield self.redis.set(self.orderbook_key, None)

        # Start fetching the base orderbook from self.url the request poller will call
        # parse_response with the response.
        self.get_request()

        self.subscribe_to_websocket()

    @defer.inlineCallbacks
    def onMessage(self, payload, isBinary):
        payload = json.loads(payload)

        if payload['event'] == u'data':
            should_continue = yield self.check_should_continue()

            if not should_continue:
                yield self.redis.set(self.orderbook_key, None)
                return

            self.message_count += 1
            orderbook_change = json.loads(payload['data'])

            orderbook_change['bids'] = [
                ['{0:.2f}'.format(float(b[0])), b[1]] for b in orderbook_change['bids']
            ]

            orderbook_change['asks'] = [
                ['{0:.2f}'.format(float(b[0])), b[1]] for b in orderbook_change['asks']
            ]

            current_timestamp = Delorean().epoch

            if not self.first_change_timestamp:
                self.first_change_timestamp = current_timestamp

            if self.orderbook and not self.orderbook_change_backlog:
                # NO Backlog of changes, apply the change.
                self.apply_change_to_orderbook(orderbook_change)

                self.publish_orderbook()

                return
            elif self.orderbook and self.orderbook_change_backlog:
                log.msg('Working down the backlog')

                # Adding current update to backlog.
                self.orderbook_change_backlog[current_timestamp] = orderbook_change

                # Working down the backlog.
                orderbook_backlog_timestamps = sorted(
                    self.orderbook_change_backlog.keys(),
                )

                for ts in orderbook_backlog_timestamps:
                    if ts > self.orderbook_timestamp:
                        log.msg('Applying Change from TS:%s to Orderbook TS:%s' % (
                            ts,
                            self.orderbook_timestamp,
                        ))

                        self.apply_change_to_orderbook(
                            self.orderbook_change_backlog.pop(ts),
                        )
                    else:
                        # This update is too old. get rid of it.
                        self.orderbook_change_backlog.pop(ts)

                self.publish_orderbook()

                return
            else:
                log.msg('Bitstamp Orderbook Not Ready. Orderbook TS:%s must be > %s' % (
                    self.orderbook_timestamp,
                    self.first_change_timestamp,
                ))

                current_timestamp = Delorean().epoch
                self.orderbook_change_backlog[current_timestamp] = orderbook_change

                return
        else:
            log.msg('Payload: %s' % payload)

    # HELPER FUNCTIONS

    def apply_change_to_orderbook(self, change):
        bids_changes = self.parse_orders(change['bids'])
        asks_changes = self.parse_orders(change['asks'])

        # Remove the 0 volumes from the orderbook.
        self.orderbook['bids'].update(bids_changes)

        for k, v in self.orderbook['bids'].iteritems():
            if v == "0":
                self.orderbook['bids'].pop(k)

        # Re-sort the bids.
        self.orderbook['bids'] = OrderedDict(sorted(
            self.orderbook['bids'].iteritems(),
            key=lambda (k, v): float(k),
            reverse=True,
        ))

        self.orderbook['asks'].update(asks_changes)

        for k, v in self.orderbook['asks'].iteritems():
            if v == "0":
                self.orderbook['asks'].pop(k)

        # Re-sort the asks.
        self.orderbook['asks'] = OrderedDict(
            sorted(self.orderbook['asks'].iteritems(), key=lambda (k, v): float(k)),
        )

    def parse_orders(self, orders):
        """Returns a price keyed orders"""
        orders_dict = OrderedDict()

        for order in orders:
            orders_dict[order[0]] = order[1]

        return orders_dict

    def get_orderbook_to_publish(self):
        """Returns a string keyed orderbook from price keyed"""
        price_key_orderbook = self.orderbook

        return {
            'bids': [[k, v, ''] for k, v in price_key_orderbook['bids'].iteritems()],
            'asks': [[k, v, ''] for k, v in price_key_orderbook['asks'].iteritems()],
        }

