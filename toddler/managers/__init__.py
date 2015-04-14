__author__ = 'michal'

import pika
from toddler import exceptions
import ujson
from toddler import logging as t_logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, Future, ProcessPoolExecutor
import time
from mongoengine import connect


def json_task(func):
    """
    Decorator for easier json decoding for RabbitManager
    :param func:
    :return:
    """
    def wrapper(self, body):
        return func(self, ujson.loads(body.decode("utf8")))

    return wrapper


class RequeueMessage(Exception):
    pass


class BaseManager(object):
    """Base Manager class"""

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def process_task_async(self, msg, loop=None):
        
        result = loop.run_in_executor(
            None,
            self.process_task,
            msg
        )
        
        return result

    def process_task(self, msg):
        """

        `We are in thread, no asyncio please, as we do not attach event loop
         here`

        :param msg:
        :return:
        """
        
        raise NotImplemented


class _TaskRunnerDataProtocol(asyncio.SubprocessProtocol):
    
    def __init__(self, exit_future: asyncio.Future):
        
        self.exit_future = exit_future
        self.output = bytearray()
        
    def pipe_data_received(self, fd, data):
        self.output.extend(data)
        
    def process_exited(self):
        self.exit_future.set_result(self.output)


class RabbitManager(BaseManager):
    """Base for managers that connects to rabbit

    """
    def __init__(self, rabbitmq_url=None, queue=None, routing_key=None,
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

        :param str rabbitmq_url: optional url to rabbitmq
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
        self._max_tasks = 3  # 2 cores + 1
        self._tasks_number = 0
        self._executor = ThreadPoolExecutor(max_workers=3)

        try:
            if rabbitmq_url is None:
                self._rabbitmq_url = config['rabbit']['url']
            else:
                self._rabbitmq_url = rabbitmq_url

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
                    self._exchange_type = "direct"
            else:
                self._exchange_type = exchange_type
        except (KeyError, TypeError) as e:
            raise exceptions.NotConfigured(str(e))
        if log is None:
            try:
                log_config = self._config['logging']
                self.log = t_logging.setup_logging(log,
                                                   self.__class__.__name__,
                                                   log_config)
            except (KeyError, TypeError):
                log_config = None
        else:
            self.log = log



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
        self.log.info("Channel opened")
        self._channel = channel
        self._channel.add_on_close_callback(self.on_channel_closed)
        self.start_consuming()

    def close_channel(self):
        self.log.info("Closing channel")
        self._channel.close()

    def open_channel(self):
        self.log.info("Opening channel")
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_connection_open(self, connection):

        self.log.info("Connected")
        self._connection = connection
        self._connection.add_on_close_callback(self.on_connection_closed)
        self.open_channel()

    def connect(self):
        """Connects to rabbitmq server, according to config
        :return pika.SelectConnection:
        """
        self.log.info("Connecting to RabbitMQ")
        return pika.SelectConnection(
            pika.URLParameters(self._rabbitmq_url),
            self.on_connection_open,
            stop_ioloop_on_close=False

        )
    
    def on_cancel_ok(self, frame):
        """Invoked when locale Basic.Cancel is acknowledged by RabbitMQ

        :param pika.frame.Method frame:
        :return:
        """

        self.log.info("Rabbit acknowledged the cancel of the consumer")
        self.close_channel()

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.

        :param pika.frame.Method method_frame: The Basic.Cancel frame
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
        
    def requeue_message(self, delivery_tag):
        """
        
        :param delivery_tag: 
        :return:
        """
        self.log.info("Requeuing message %s", delivery_tag)
        self._channel.basic_nack(delivery_tag, requeue=True)

    def on_message(self, channel, basic_deliver, properties, body):
        """Invoked when message received from rabbit

        :param pika.channel.Channel channel:
        :param pika.spec.Basic.Deliver basic_deliver:
        :param pika.spec.BasicProperties properties:
        :param str body:
        :return:
        """

        self.log.info("Received messages # %s from %s",
                      basic_deliver.delivery_tag,
                      properties.app_id)
        
        try:
            if self._tasks_number >= self._max_tasks:
                raise RuntimeError("Max tasks limit reached")
            
            self._tasks_number += 1
            
            ftr = self._executor.submit(self.process_task, body)

            def process_done(future: Future):
                nonlocal self
                if future.cancelled():
                    # process_task ended by cancel
                    self.requeue_message(self.requeue_message(
                        basic_deliver.delivery_tag)
                    )
                else:
                    if future.exception():
                        self.log.exception(future.exception())
                        
                        self.requeue_message(
                            basic_deliver.delivery_tag
                        )
                    else:
                        self.acknowledge_message(basic_deliver.delivery_tag)
                self._tasks_number -= 1
                
            ftr.add_done_callback(process_done)

        except RuntimeError:
            self.requeue_message(basic_deliver.delivery_tag)
            time.sleep(0.5)

        except Exception as e:
            self.log.exception(e)
            self.requeue_message(basic_deliver.delivery_tag)
            time.sleep(10)

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

        c = self.connect()
        """:type: pika.SelectConnection"""
        c.ioloop.start()
            
    def stop(self):
        """Stops consuming service
        :return:
        """

        self.log.info("Stopping")
        self._closing = True
        self.stop_consuming()
        self._executor.shutdown(True)
        self._connection.ioloop.start()
        self.log.info("Stopped")
        

class RabbitManagerWithMongoDb(RabbitManager):

    def __init__(self, mongodb_url, *args, **kwargs):
        """
        :param mongodb_url:
        :param str rabbitmq_url: optional url to rabbitmq
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
        self._mongodb_url = mongodb_url
        self._connect_mongodb()
        super(RabbitManagerWithMongoDb, self).__init__(*args, **kwargs)

    def _connect_mongodb(self):
        connect(self._mongodb_url)