import os

from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import reactor
from txredis.client import RedisClient

import gryphon.data_service.consts as consts
from gryphon.data_service.twisted_producer import TwistedProducer


def setup_redis(host='localhost', port=6379):
    """Setup a twisted txredis client. Returns a Deferred"""

    clientCreator = protocol.ClientCreator(reactor, RedisClient)

    return clientCreator.connectTCP(host, port)


@defer.inlineCallbacks
def setup_producer(queue, binding_key):
    if 'AMPQ_HOST' in os.environ:
        producer = TwistedProducer(
            consts.EXCHANGE,
            consts.EXCHANGE_TYPE,
            queue,
            binding_key,
        )

        yield producer.run()

        # Returns defered.
        defer.returnValue(producer)
    else:
        raise ValueError('AMPQ_HOST Must be set in Environment')
