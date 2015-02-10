__author__ = 'michal'
from unittest import TestCase

from toddler.managers import workermanager
from toddler.workers import gear_worker
from toddler.logging import setup_logging
from toddler.utils import run_process
import gear
import asyncio
import sys


class TestGearWorker(gear_worker.GearWorker):

    def __init__(self, gear_servers, log=None):

        super(TestGearWorker, self).__init__(
            gear_servers,
            'testWorker',
            'parse_document',
            log
        )

    def handle_job(self, job: gear.WorkerJob):
        self.log.info("job: " + job.arguments.decode("utf8"))
        self.stop()


class TestGear(TestCase):

    def test_gear_integration(self):

        config = {
            "rabbit": {
                "url": "amqp://webapp:webapp@fliv-dev/",
                "queue": "test",
                "routingKey": "test",
                "exchange": "test",
                "exchangeType": "direct"
            },
            "logging": {
                'version': 1,
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'level': 'DEBUG',
                        'stream': 'ext://sys.stdout'
                    }
                }
            }
        }

        wm = workermanager.DocumentWorkerManager(['192.168.50.101'],
                                                 config=config)
        msg = b'{"msg":"document"}'
        wm.process_task(msg)

        out = run_process(sys.executable, __file__)
        print(out)
        self.assertIn("job: " + msg.decode("utf8"), out)


if __name__ == '__main__':

    log = setup_logging(config={
        'handlers': {
            'console': {
                'version': 1,
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'stream': 'ext://sys.stdout'
            }
        }
    })

    gw = TestGearWorker(['192.168.50.101'], log)

    asyncio.get_event_loop().run_until_complete(gw.start())

