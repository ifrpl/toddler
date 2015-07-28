__author__ = 'michal'

import pika
import asyncio
from concurrent.futures import Future
from pika_pool import QueuedPool

_pools = {}

def blocking_connection(rabbit_url):

    return pika.BlockingConnection(pika.URLParameters(rabbit_url))

def get_pool(rabbit_url):

    try:
        return _pools[rabbit_url]
    except KeyError:

        pool = QueuedPool(
            create=lambda: blocking_connection(rabbit_url),
            max_size=10,
            max_overflow=10,
            timeout=10,
            recycle=3600,
            stale=45,
        )

        _pools[rabbit_url] = pool
        return pool

def send_message_sync(rabbit_url, message, routing_key, exchange=""):
    """
    Send message to rabbit mq synchronously
    
    :param rabbit_url: 
    :param message: 
    :param queue: 
    :param exchange: 
    :param routing_key: 
    :return:
    """

    with get_pool(rabbit_url).acquire() as connection:
        ch = connection.channel()

        ch.confirm_delivery()

        if ch.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=message,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=1
            )):
            connection.close()
        else:
            connection.close()
            raise ValueError


def send_message(rabbit_url, message, routing_key, exchange=""):
    """
    
    :param rabbit_url:
    :param message:
    :param queue:
    :param exchange:
    :param routing_key:
    :return asyncio.Future:
    """
    
    future = asyncio.Future()
    
    @asyncio.coroutine
    def _send():
        
        try:
            send_message_sync(rabbit_url, message, routing_key, exchange)
            future.set_result(True)
        except Exception as e:
            future.set_exception(e)
            
    asyncio.async(_send())

    return future


def declare_queue(rabbit_url, queue_name):
    """
    Declares queue and returns Future object

    :param channel:
    :param queue_name:
    :return:
    """

    with get_pool(rabbit_url).acquire() as connection:

        channel = connection.channel()

        ftr = Future()

        exchange_name = "{}_exchange".format(queue_name)

        def queue_declared():
            nonlocal ftr
            ftr.set_result((queue_name, exchange_name))

        def bind_queue_to_exchange(*args, **kwargs):
            nonlocal channel
            channel.queue_bind(queue_declared, queue_name, exchange_name,
                               exchange_name)

        def declare_exchange(*args, **kwargs):
            nonlocal channel, exchange_name
            channel.exchange_declare(bind_queue_to_exchange,
                                     exchange=exchange_name)

        channel.queue_declare(callback=declare_exchange, queue=queue_name,
                              durable=True, auto_delete=False)

        return ftr
