import json

from delorean import Delorean
from twisted.internet import defer
from twisted.python import log

import gryphon.data_service.consts as consts
from gryphon.data_service.pollers.request_poller import RequestPoller
import gryphon.data_service.util as util


class OrderbookPoller(RequestPoller):
    @property
    def orderbook_key(self):
        return '%s_orderbook' % self.exchange_name.lower()

    @property
    def heartbeat_key(self):
        return '%s_orderbook_heartbeat' % self.exchange_name.lower()

    @defer.inlineCallbacks
    def start(self):
        binding_key = '%s.orderbook.tinker' % self.exchange_name.lower()
        self.producer = yield util.setup_producer(consts.ORDERBOOK_QUEUE, binding_key)

        super(OrderbookPoller, self).start()

    def get_bids_and_asks(self, raw_orderbook):
        raw_bids = raw_orderbook['bids']
        raw_asks = raw_orderbook['asks']

        return raw_bids, raw_asks

    def parse_orderbook(self, raw_bids, raw_asks):
        bids = []
        asks = []

        for raw_bid in raw_bids:
            bid = self.parse_order(raw_bid)
            bids.append(bid)

        for raw_ask in raw_asks:
            ask = self.parse_order(raw_ask)
            asks.append(ask)

        return bids, asks

    @defer.inlineCallbacks
    def parse_response(self, response):
        raw_bids, raw_asks = self.get_bids_and_asks(response)

        bids, asks = self.parse_orderbook(raw_bids, raw_asks)

        new_orderbook = {
            'timestamp': Delorean().epoch,
            self.exchange_name: {
                'bids': bids,
                'asks': asks,
            }
        }

        current_orderbook_string = yield self.redis.get(self.orderbook_key)

        if not current_orderbook_string:
            current_orderbook_string = ''

        new_orderbook_string = json.dumps(new_orderbook, ensure_ascii=False)

        # TODO: These will never be the same because of the timestamp.
        if current_orderbook_string != new_orderbook_string:
            # There is a new orderbook. Save it and publish it.
            yield self.redis.set(self.orderbook_key, new_orderbook_string)

            if self.producer:
                self.producer.publish_message(new_orderbook_string)
        else:
            log.msg('No Changes on %s' % self.exchange_name)
