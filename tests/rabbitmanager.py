__author__ = 'michal'


from toddler.managers import RabbitManager
import unittest
import asyncio
import asyncio.subprocess
from toddler.rabbit_sender import send_message_sync, send_message
import logging
import sys
import json
from toddler.utils import run_process
import time


class _TestRabbit(RabbitManager):

    def process_task(self, msg):
        
        msg = json.loads(msg.decode("utf8"))
        self.log.info("msg: " + msg['msg'])


class TestRabbitManager(unittest.TestCase):

    def setUp(self):

        self.future = asyncio.Future()
        self.loop = asyncio.get_event_loop()

    def test_rabbit(self):

        for x in range(0, 20):
            print("Sending msg", x)
            send_message_sync("amqp://webapp:webapp@fliv-dev/",
                              '{"msg": "true", "id": '+str(x)+'}',
                              "test")

        out = run_process(sys.executable, __file__)
        
        print(out.decode("utf8"))
        
        self.assertIn("msg: true", out.decode("utf8"))
        
        self.assertEqual(out.decode("utf8").count("msg: true"), 20)


if __name__ == "__main__":
    config = {
        "rabbit": {
            "url": "amqp://webapp:webapp@fliv-dev/",
            "queue": "test",
            "routingKey": "test",
            "exchange": "test",
            "exchangeType": "direct"
        }
    }

    log = logging.getLogger("RabbitTest")

    log.setLevel(logging.DEBUG)
    lh = logging.StreamHandler(sys.stdout)
    log.addHandler(lh)

    log.debug("Starting RabbitTest instance")

    rm = _TestRabbit(config=config, log=log)
    try:
        rm.run()
    except KeyboardInterrupt:
        try:
            rm.stop()
        except KeyboardInterrupt:
            pass

    log.debug("Stopped RabbitTEst instance")

