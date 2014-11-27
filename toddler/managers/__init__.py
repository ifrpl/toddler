__author__ = 'michal'

__author__ = 'michal'

import logging
import logging.config
import pika
from toddler import exceptions
import json

class BaseManager(object):
    """Base Manager class"""

    def process_task(self, msg):
        """

        :param dict msg:
        :return:
        """
        raise NotImplemented

class RabbitManager(BaseManager):
    """Base for managers that connects to rabbit

    """
    def __init__(self, url=None, queue=None, routing_key=None,
                 exchange=None, exchange_type=None, config=None, log=None):
        """

        # Config dict structure (case adjusted to json configuration):
        {
            "rabbit": {
                "url": "apmq://rabbit",
                "queue": "test",
                "routingKey": "example.json"
                "exchange": "message", // optional, default: message
                "exchangeType:" "topic" // optional, default: topic
            }
        }

        :param str url: optional url to rabbitmq
        :param str queue: name of the queue
        :param str routing_key: routing key for queue
        :param str exchange: name of the exchange
        :param str exchange_type: type of the exchange
        :param dict config: Manager configuration from parsed json config all
                            the above options can be configured from it
        :param logging.Logger log: optional logger that will replace new one
        :raises exceptions.NotConfigured:
        :return:
        """

        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._config = config
        try:
            if url is None:
                self._url = config['rabbit']['url']
            else:
                self._url = url

            if queue is None:
                self._queue = config['rabbit']['queue']
            else:
                self._queue = queue

            if routing_key is None:
                self._routing_key = config['rabbit']['routingKey']
            else:
                self._routing_key = routing_key

            if exchange is None:
                try:
                    self._exchange = config['rabbit']['exchange']
                except KeyError:
                    # setting defaults
                    self._exchange = "message"
            else:
                self._exchange = exchange

            if exchange_type is None:
                try:
                    self._exchange_type = config['rabbit']['exchangeType']
                except KeyError:
                    # setting defaults
                    self._exchange_type = "topic"
            else:
                self._exchange_type = exchange_type
        except KeyError as e:
            raise exceptions.NotConfigured(str(e))

        self.log = None
        self.setup_logging(log)

    def setup_logging(self, logger=None):
        """
        Sets up logging for this process
        :param logger: optional logger that will be used by manager
        :return None:
        """

        if logger is None:

            try:
                logging.config.dictConfig(self._config['logging'])
                self.log = logging.getLogger(self.__class__.__name__)
            except KeyError:
                logging.warning(
                    "Logging not configured for %s" % self.__class__.__name__
                )
                self.log = logger
                self.log.setLevel(logging.DEBUG)


        else:
            self.log = logger

    def reconnect(self):
        """Will be run by IOLoop.time if the connection is closed.
        See on_connection_closed method.
        """
        self._connection.ioloop.stop()

        if not self._closing:
            self._connection = self.connect()
            self._connection.ioloop.start()

    def on_connection_closed(self, connection, reply_code, reply_text):
        """

        :param pika.connection.Connection connection: closed connection ob
        :param int reply_code: reply code if given
        :param str reply_text: reply text if given
        :return:
        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            self.log.warning(
                "Connection closed, will reopen in 5 seconds: (%s) %s",
                reply_code,
                reply_text
            )

            self._connection.add_timeout(5, self.reconnect)

    def on_channel_closed(self, channel, reply_code, reply_text):
        """Invoked when channel has been closed

        :param pika.channel.Channel channel:
        :param int reply_code:
        :param str reply_text:
        :return:
        """
        self.log.warning("Channel to rabbit closed.")
        self._connection.close()

    def on_channel_open(self, channel):
        """Invoked when channel has been opened

        :param pika.channel.Channel channel:
        """
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)

    def close_channel(self):
        self.log.info("Closing channel")
        self._channel.close()

    def open_channel(self):
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_connection_open(self, connection):

        self.log.info("Connected")
        self._connection.add_on_close_callback(self.on_connection_closed)
        self.open_channel()

    def connect(self):
        """Connects to rabbitmq server, according to config
        :return:
        """
        self.log.info("Connecting to RabbitMQ")
        return pika.SelectConnection(
            pika.URLParameters(self._url),
            self.on_connection_open,
            stop_ioloop_on_close=False
        )

    def on_cancel_ok(self, frame):
        """Invoked when locale Basic.Cancel is acknowledged by RabbitMQ

        :param frame:
        :return:
        """

        self.log.info("Rabbit acknowledged the cancel of the consumer")
        self.close_channel()

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.method.frame method_frame: The Basic.Cancel frame
        :return:
        """
        self.log.info("Consumer was cancelled remotely, shutting down: %r",
                      method_frame)
        if self._channel:
            self._channel.close()

    def acknowledge_message(self, delivery_tag):
        """

        :param delivery_tag:
        :return:
        """
        self.log.info("Acknowledging message %s", delivery_tag)
        self._channel.basic_ack(delivery_tag)

    def on_message(self, channel, basic_deliver, properties, body):
        """Invoked when message received from rabbit

        :param pika.channel.Channel channel:
        :param pika.spec.Basic.Deliver basic_deliver:
        :param pika.spec.BasicProperties properties:
        :param str body:
        :return:
        """

        self.log.info("Received messsages # %s from %s",
                      basic_deliver.delivery_tag,
                      properties.app_id)

        self.acknowledge_message(basic_deliver.delivery_tag)


        if properties.content_type == "application/json":
            self.process_task(json.loads(body))
        else:
            self.process_task(body)



    def stop_consuming(self):
        """Send Basic.Cancel to rabbit

        :return:
        """

        if self._channel:
            self.log.info("Stop consuming")
            self._channel.basic_cancel(self.on_cancel_ok, self._consumer_tag)

    def start_consuming(self):
        """Begins to consume messages

        :return:
        """

        self.log.info("Start consuming")

        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)
        self._consumer_tag = self._channel.basic_consume(self.on_message,
                                                         self._queue)


    def run(self):
        """Run consumer"""
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Stops consuming service
        :return:
        """

        self.log.info("Stopping")
        self._closing = True
        self.stop_consuming()
        self._connection.ioloop.start()
        self.log.info("Stopped")

