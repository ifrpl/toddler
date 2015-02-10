__author__ = 'michal'

import pika


def send_message(rabbit_url, message, queue, exchange, routing_key):

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




