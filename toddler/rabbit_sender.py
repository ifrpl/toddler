__author__ = 'michal'

import pika
import asyncio


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

    connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))

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

