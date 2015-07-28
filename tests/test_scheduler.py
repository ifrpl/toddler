__author__ = 'michal'

from unittest import mock, TestCase
from mongomock import Connection

# mocking mongo connection
mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()
from datetime import datetime, timezone, timedelta
import ujson
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

        s = Scheduler(rabbitmq_url="amqp://localhost", exchange='CrawlRequest',
                      routing_key='CrawlRequest')

        s.schedule_jobs_for_hosts()

        host = Host.objects(host=self.host.host).first()

        self.assertEqual(
            host.last_crawl_job_date.date(),
            datetime.utcnow().date()
        )
        # self.assertTrue(send_message.called)

    @mock.patch("toddler.rabbit_sender.send_message_sync")
    def test_analysis_task_delay_queue(self, send_message):

        from toddler.scheduler import AnalysisTaskDelayQueueObserver

        a = AnalysisTaskDelayQueueObserver(rabbitmq_url="amqp://localhost",
                                           queue='AnalysisTaskDelayQueue',
                                           exchange="AnalysisTask",
                                           routing_key='AnalysisTask')

        d = {
            "delay_reason": "test reason",
            "timeout": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "message": {
                "test": "test"
            }
        }
        a.process_task(
            ujson.dumps(d).encode("utf8")
        )

        self.assertTrue(send_message.called)
        self.assertEqual(send_message.call_args[0][1],
                         ujson.dumps({"test": "test"}))


