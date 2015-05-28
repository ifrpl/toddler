__author__ = 'michal'

from unittest import mock, TestCase
from mongomock import Connection

# mocking mongo connection
mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()
import datetime
from toddler.models import Host
from toddler import setup


class SchedulerTest(TestCase):

    @classmethod
    def setUpClass(cls):
        setup(['-m', 'mongodb://localhost'],
              do_not_parse_config=True)

        super(SchedulerTest, cls).setUpClass()

    def setUp(self):

        self.host = Host(host="example.com")
        self.host.save()


    @mock.patch("toddler.rabbit_sender.send_message_sync")
    def test_scheduling(self, send_message):

        from toddler.scheduler import Scheduler

        s = Scheduler(rabbit_url="ampq://localhost", exchange='CrawlRequest',
                      routing_key='CrawlRequest')

        try:
            s.run()
        except KeyboardInterrupt:
            pass

        host = Host.objects(host=self.host.host).first()

        self.assertEqual(
            host.last_crawl_job_date.date(),
            datetime.datetime.now().date()
        )

        self.assertTrue(send_message.called)