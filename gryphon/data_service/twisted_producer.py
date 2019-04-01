# -*- coding: utf-8 -*-
import os

import pika
from pika.adapters import twisted_connection
from twisted.internet import defer, reactor, protocol, task
from twisted.python import log


class TwistedProducer(object):
    """
    This is an example producer that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.

    If RabbitMQ closes the connection, it will reopen it. You should
    look at the output, as there are limited reasons why the connection may
    be closed, which usually are tied to permission related issues or
    socket timeouts.

    It uses delivery confirmations and illustrates one way to keep track of
    messages that have been sent and if they've been confirmed by RabbitMQ.
    """

    def __init__(self, exchange, exchange_type, queue, binding_key):
        """
        Setup the example producer object, passing in the URL we will use to connect to
        RabbitMQ.
        """

        self._connection = None
        self._channel = None
        self._deliveries = []
        self._acked = 0
        self._nacked = 0
        self._message_number = 0
        self._stopping = False
        self._closing = False
        self.ready = False

        self.exchange = exchange
        self.exchange_type = exchange_type
        self.queue_name = queue
        self.binding_key = binding_key

    def report_error(self, error):
        log.err('Error in Twisted Producer:%s' % str(error))

    def connect(self):
        """
        This method connects to RabbitMQ, returning the connection handle.  When the
        connection is established, the on_connection_open method will be invoked by
        pika. If you want the reconnection to work, make sure you set
        stop_ioloop_on_close to False, which is not the default behavior of this
        adapter.

        :rtype: pika.SelectConnection
        """

        credentials = pika.PlainCredentials(
            os.environ['AMPQ_USER'],
            os.environ['AMPQ_PASS'],
        )

        parameters = pika.ConnectionParameters(
            os.environ['AMPQ_HOST'],
            int(os.environ['AMPQ_PORT']),
            '/',
            credentials,
        )

        parameters = pika.ConnectionParameters()

        cc = protocol.ClientCreator(
            reactor,
            twisted_connection.TwistedProtocolConnection,
            parameters,
        )

        d = cc.connectTCP('localhost', 5672)
        d.addCallback(lambda protocol: protocol.ready)
        d.addCallback(self.on_connection_open)
        d.addErrback(self.report_error)

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""

        log.msg('Closing connection')

        self._closing = True
        self._connection.close()

    def on_connection_closed(self, connection, reply_code, reply_text):
        """
        This method is invoked by pika when the connection to RabbitMQ is closed
        unexpectedly. Since it is unexpected, we will reconnect to RabbitMQ if it
        disconnects.

        :param pika.connection.Connection connection: The closed connection obj
        :param int reply_code: The server provided reply_code if given
        :param str reply_text: The server provided reply_text if given

        """
        self._channel = None

        if self._closing:
            self.ready = False
        else:
            log.err(
                'Connection closed, reopening in 5 seconds: (%s) %s',
                reply_code,
                reply_text,
            )

            self._connection.add_timeout(5, self.reconnect)

    @defer.inlineCallbacks
    def on_connection_open(self, connection):
        """
        This method is called by pika once the connection to RabbitMQ has been
        established. It passes the handle to the connection object in case we need it.

        :type unused_connection: pika.SelectConnection
        """

        try:
            self.ready = False

            self._connection = connection
            self._connection.add_on_close_callback(self.on_connection_closed)

            self._channel = yield connection.channel()
            self._channel.add_on_close_callback(self.on_channel_closed)

            self._exchange = yield self._channel.exchange_declare(
                exchange=self.exchange,
                type=self.exchange_type,
            )

            self._queue = yield self._channel.queue_declare(
                queue=self.queue_name,
                auto_delete=False,
                exclusive=False,
                durable=True,
            )

            yield self._channel.queue_bind(
                exchange=self.exchange,
                queue=self.queue_name,
                routing_key=self.binding_key,
            )

            self._channel.confirm_delivery(self.on_delivery_confirmation)
            self.ready = True

        except Exception as e:
            self.report_error(e)

    def reconnect(self):
        """
        Will be invoked by the IOLoop timer if the connection is closed. See the
        on_connection_closed method.
        """

        # Create a new connection
        self.connect()

    def on_channel_closed(self, channel, reply_code, reply_text):
        """
        Invoked by pika when RabbitMQ unexpectedly closes the channel. Channels are
        usually closed if you attempt to do something that violates the protocol, such
        as re-declare an exchange or queue with different parameters. In this case,
        we'll close the connection to shutdown the object.

        :param pika.channel.Channel: The closed channel
        :param int reply_code: The numeric reason the channel was closed
        :param str reply_text: The text reason the channel was closed
        """

        log.err('Channel was closed: (%s) %s' % (reply_code, reply_text))

        if not self._closing:
            self._connection.close()

    def on_delivery_confirmation(self, method_frame):
        """
        Invoked by pika when RabbitMQ responds to a Basic.Publish RPC command, passing
        in either a Basic.Ack or Basic.Nack frame with the delivery tag of the message
        that was published. The delivery tag is an integer counter indicating the
        message number that was sent on the channel via Basic.Publish. Here we're just
        doing house keeping to keep track of stats and remove message numbers that we
        expect a delivery confirmation of from the list used to keep track of messages
        that are pending confirmation.

        :param pika.frame.Method method_frame: Basic.Ack or Basic.Nack frame
        """

        confirmation_type = method_frame.method.NAME.split('.')[1].lower()

        if confirmation_type == 'ack':
            self._acked += 1
        elif confirmation_type == 'nack':
            self._nacked += 1

        self._deliveries.remove(method_frame.method.delivery_tag)

    @defer.inlineCallbacks
    def wait_until_ready(self):
        def offline_check_if_ready(self):
            return self.ready

        is_ready = self.ready

        while not is_ready:
            is_ready = yield task.deferLater(reactor, 1, offline_check_if_ready, self)

    def publish_message(self, message):
        """
        If the class is not stopping, publish a message to RabbitMQ, appending a list of
        deliveries with the message number that was sent. This list will be used to
        check for delivery confirmations in the on_delivery_confirmations method.
        """

        if not self.ready:
            raise ValueError('Producer not ready befor message published.')

        if self._stopping:
            log.msg('Producer is Stopping')
            return

        if not self._channel:
            log.err('No Channel Avaialble')
            return

        properties = pika.BasicProperties(
            app_id=u'example-producer',
            content_type=u'application/json',
            delivery_mode=2,
        )

        self._channel.basic_publish(
            self.exchange,
            self.binding_key,
            message,
            properties,
        )

        self._message_number += 1
        self._deliveries.append(self._message_number)

    def close_channel(self):
        """
        Invoke this command to close the channel with RabbitMQ by sending the
        Channel.Close RPC command.
        """

        log.msg('Closing the channel')

        if self._channel:
            self._channel.close()

    def run(self):
        """
        Run the example code by connecting.
        """

        self.connect()

        # Wait until ready.
        return task.deferLater(reactor, 1, self.wait_until_ready)

    def stop(self):
        """
        Stop the example by closing the channel and connection. We set a flag here so
        that we stop scheduling new messages to be published. The IOLoop is started
        because this method is invoked by the Try/Catch below when KeyboardInterrupt is
        caught. Starting the IOLoop again will allow the producer to cleanly disconnect
        from RabbitMQ.
        """

        log.msg('Stopping')

        self._stopping = True
        self.close_channel()
        self.close_connection()

        log.msg('Stopped')

