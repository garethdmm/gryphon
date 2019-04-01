import json

from delorean import Delorean
from twisted.internet import defer

from gryphon.data_service.pollers.orderbook.orderbook_poller import OrderbookPoller
from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


class WebsocketOrderbookPoller(OrderbookPoller):
    AMQP_PUSH_MAX_FREQUENCY = 1  # Seconds.

    def start(self):
        # Don't do any setup in here, because connect_to_websocket creates a new
        # instance.
        self.connect_to_websocket()

        # We are deliberately avoiding calling super() because we don't want to start
        # a looping call to get_request.

    @defer.inlineCallbacks
    def restart(self):
        yield self.onOpen()

    @defer.inlineCallbacks
    def publish_orderbook(self):
        new_orderbook = self.get_orderbook_to_publish()

        orderbook_has_changed = yield self.check_if_orderbook_has_changed(new_orderbook)

        new_orderbook_with_metadata = {
            'timestamp': Delorean().epoch,
            self.exchange_name: new_orderbook,
        }

        new_orderbook_string = json.dumps(new_orderbook_with_metadata)

        self.heartbeat()

        # We always publish to Redis, even if the orderbook has not changed
        # so that the timestamp gets updated correctly
        logger.debug('Publishing orderbook to Redis')
        yield self.redis.set(self.orderbook_key, new_orderbook_string)

        seconds_since_last_amqp_push = Delorean().epoch - self.last_amqp_push
        if (self.producer and orderbook_has_changed and
                seconds_since_last_amqp_push > self.AMQP_PUSH_MAX_FREQUENCY):
            logger.debug('Publishing orderbook on AMQP')
            self.producer.publish_message(new_orderbook_string)
            self.last_amqp_push = Delorean().epoch

    @defer.inlineCallbacks
    def check_if_orderbook_has_changed(self, new_orderbook):
        orderbook_has_changed = True

        old_orderbook_string = yield self.redis.get(self.orderbook_key)
        if old_orderbook_string and old_orderbook_string != "None":
            old_orderbook = json.loads(old_orderbook_string)

            if old_orderbook[self.exchange_name] == new_orderbook:
                orderbook_has_changed = False

        defer.returnValue(orderbook_has_changed)

    @defer.inlineCallbacks
    def check_should_continue(self):
        should_continue_key = '%s_orderbook_should_continue' % self.exchange_name.lower()
        should_continue = yield self.redis.get(should_continue_key)
        if not should_continue:
            raise KeyError('Expecting %s key in redis.' % should_continue_key)
        should_continue = bool(int(should_continue))

        if not should_continue:
            logger.debug('%s Orderbook Poller respecting Auditor hard failure.' % self.exchange_name)

        defer.returnValue(should_continue)
