# -*- coding: utf-8 -*-
import subprocess
import time

import pika

from gryphon.lib.logger import get_logger

logger = get_logger('emerald-havoc-consumer')


class QueueConsumerException(Exception):
    pass


class QueueConsumer(object):
    """
    This is an example consumer that will handle unexpected interactions with RabbitMQ
    such as channel and connection closures.

    If RabbitMQ closes the connection, it will reopen it. You should look at the output,
    as there are limited reasons why the connection may be closed, which usually are
    tied to permission related issues or socket timeouts.

    If the channel is closed, it will indicate a problem with one of the commands that
    were issued and that should surface in the output as well.
    """

    def __init__(self, amqp_url, consumer_func, consumer_func_args, exchange, exchange_type, binding_key, queue_name):
        """
        Create a new instance of the consumer class, passing in the AMQP URL used to
        connect to RabbitMQ.

        :param str amqp_url: The AMQP url to connect with
        """

        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._url = amqp_url

        self.consumer_func = consumer_func
        self.consumer_func_args = consumer_func_args

        self.exchange = exchange
        self.exchange_type = exchange_type
        self.binding_key = binding_key
        self.queue_name = queue_name

    def connect(self):
        """
        This method connects to RabbitMQ, returning the connection handle.  When the
        connection is established, the on_connection_open method will be invoked by
        pika.

        :rtype: pika.SelectConnection
        """

        logger.info('Connecting to %s', self._url)

        return pika.SelectConnection(
            pika.URLParameters(self._url),
            self.on_connection_open,
            stop_ioloop_on_close=False,
        )

    def close_connection(self):
        """This method closes the connection to RabbitMQ."""

        logger.info('Closing connection')
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
            self._connection.ioloop.stop()
        else:
            logger.warning(
                'Connection closed, reopening in 5 seconds: (%s) %s',
                reply_code,
                reply_text,
            )

            self._connection.add_timeout(5, self.reconnect)

    def on_connection_open(self, unused_connection):
        """
        This method is called by pika once the connection to RabbitMQ has been
        established. It passes the handle to the connection object in case we need it,
        but in this case, we'll just mark it unused.

        :type unused_connection: pika.SelectConnection
        """

        logger.info('Connection opened')
        logger.info('Adding connection close callback')

        self._connection.add_on_close_callback(self.on_connection_closed)
        self._connection.channel(on_open_callback=self.on_channel_open)

    def reconnect(self):
        """
        Will be invoked by the IOLoop timer if the connection is closed. See the
        on_connection_closed method.
        """

        # This is the old connection IOLoop instance, stop its ioloop.
        self._connection.ioloop.stop()

        if not self._closing:
            # Create a new connection.
            self._connection = self.connect()

            # There is now a new connection, needs a new ioloop to run.
            self._connection.ioloop.start()

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

        logger.warning(
            'Channel %i was closed: (%s) %s',
            channel,
            reply_code,
            reply_text,
        )

        self._connection.close()

    def on_channel_open(self, channel):
        """
        This method is invoked by pika when the channel has been opened. The channel
        object is passed in so we can make use of it.

        Since the channel is now open, we'll declare the exchange to use.

        :param pika.channel.Channel channel: The channel object
        """

        logger.info('Channel opened')

        self._channel = channel

        logger.info('Adding channel close callback')

        self._channel.add_on_close_callback(self.on_channel_closed)

        logger.info('Declaring exchange %s', self.exchange)

        self._channel.exchange_declare(
            self.on_exchange_declareok,
            self.exchange,
            self.exchange_type,
        )

    def on_exchange_declareok(self, unused_frame):
        """
        Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC command.

        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame
        """

        logger.info('Exchange declared')
        logger.info('Declaring queue %s', self.queue_name)

        self._channel.queue_declare(
            self.on_queue_declareok,
            self.queue_name,
            durable=True,
        )

    def on_queue_declareok(self, method_frame):
        """
        Method invoked by pika when the Queue.Declare RPC call made in setup_queue has
        completed. In this method we will bind the queue and exchange together with the
        routing key by issuing the Queue.Bind RPC command. When this command is complete
        , the on_bindok method will be invoked by pika.

        :param pika.frame.Method method_frame: The Queue.DeclareOk frame
        """

        logger.info(
            'Binding %s to %s with %s',
            self.exchange,
            self.queue_name,
            self.binding_key,
        )

        self._channel.queue_bind(
            self.on_bindok,
            self.queue_name,
            self.exchange,
            self.binding_key,
        )

    def on_consumer_cancelled(self, method_frame):
        """
        Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer receiving
        messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """

        logger.info(
            'Consumer was cancelled remotely, shutting down: %r',
            method_frame,
        )

        if self._channel:
            self._channel.close()

    def acknowledge_message(self, delivery_tag):
        """
        Acknowledge the message delivery from RabbitMQ by sending a Basic.Ack RPC
        method for the delivery tag.

        :param int delivery_tag: The delivery tag from the Basic.Deliver frame
        """

        self._channel.basic_ack(delivery_tag)

    def on_message(self, unused_channel, basic_deliver, properties, body, attempt=1):
        """
        Invoked by pika when a message is delivered from RabbitMQ. The channel is
        passed for your convenience. The basic_deliver object that is passed in carries
        the exchange, routing key, delivery tag and a redelivered flag for the message.
        The properties passed in is an instance of BasicProperties with the message
        properties and the body is the message that was sent.

        :param pika.channel.Channel unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param str|unicode body: The message body
        """

        # https://www.rabbitmq.com/tutorials/tutorial-two-python.html
        # see Message Acknowledgement.
        # We now only heartbeat on a successful consumer_func call.
        try:
            self.consumer_func(body, self.consumer_func_args)

            heartbeat_key = self.queue_name.lower()

            subprocess.call([
                'touch',
                'monit/heartbeat/%s_consumer_success_heartbeat.txt' % heartbeat_key,
            ])

            self.acknowledge_message(basic_deliver.delivery_tag)
        except:
            logger.exception('Attempt %s: FAILED MESSAGE: %s' % (attempt, body[:100]))

            if attempt > 600:
                raise QueueConsumerException(
                    'Queue: %s has had too many failures' % self.queue_name.lower(),
                )

            # We are going to sleep for 1 second before retrying.
            time.sleep(1)

            self.on_message(
                unused_channel,
                basic_deliver,
                properties,
                body,
                attempt=attempt + 1,
            )

    def on_cancelok(self, unused_frame):
        """
        This method is invoked by pika when RabbitMQ acknowledges the cancellation of
        a consumer. At this point we will close the channel. This will invoke the
        on_channel_closed method once the channel has been closed, which will in-turn
        close the connection.

        :param pika.frame.Method unused_frame: The Basic.CancelOk frame
        """

        logger.info('RabbitMQ acknowledged the cancellation of the consumer')

        self.close_channel()

    def stop_consuming(self):
        """
        Tell RabbitMQ that you would like to stop consuming by sending the Basic.Cancel
        RPC command.
        """

        if self._channel:
            logger.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            self._channel.basic_cancel(self.on_cancelok, self._consumer_tag)

    def start_consuming(self):
        """
        This method sets up the consumer by first calling add_on_cancel_callback
        so that the object is notified if RabbitMQ cancels the consumer. It then
        issues the Basic.Consume RPC command which returns the consumer tag that is
        used to uniquely identify the consumer with RabbitMQ. We keep the value to use
        it when we want to cancel consuming. The on_message method is passed in as a
        callback pika will invoke when a message is fully received.
        """

        logger.info('Issuing consumer related RPC commands')
        logger.info('Adding consumer cancellation callback')

        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

        self._consumer_tag = self._channel.basic_consume(
            self.on_message,
            self.queue_name,
        )

    def on_bindok(self, unused_frame):
        """
        Invoked by pika when the Queue.Bind method has completed. At this point we
        will start consuming messages by calling start_consuming which will invoke the
        needed RPC commands to start the process.

        :param pika.frame.Method unused_frame: The Queue.BindOk response frame
        """

        logger.info('Queue bound')
        self.start_consuming()

    def close_channel(self):
        """
        Call to close the channel with RabbitMQ cleanly by issuing the Channel.Close
        RPC command.
        """

        logger.info('Closing the channel')
        self._channel.close()

    def run(self):
        """
        Run the example consumer by connecting to RabbitMQ and then starting the IOLoop
        to block and allow the SelectConnection to operate.
        """

        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """
        Cleanly shutdown the connection to RabbitMQ by stopping the consumer with
        RabbitMQ. When RabbitMQ confirms the cancellation, on_cancelok will be invoked
        by pika, which will then closing the channel and connection. The IOLoop is
        started again because this method is invoked when CTRL-C is pressed raising a
        KeyboardInterrupt exception. This exception stops the IOLoop which needs to be
        running for pika to communicate with RabbitMQ. All of the commands issued prior
        to starting the IOLoop will be buffered but not processed.
        """

        logger.info('Stopping')

        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()

        logger.info('Stopped')

