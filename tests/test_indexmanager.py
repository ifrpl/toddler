__author__ = 'michal'
from unittest import TestCase, mock
from mongomock import Connection
mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()
from toddler.managers.indexmanager import IndexManager
from addict import Dict
import ujson
from toddler.managers.crawlmanager import now


class IndexManagerTests(TestCase):

    def setUp(self):
        self.index_manager = IndexManager("mongodb://localhost/",
                                          rabbitmq_url="apmq://fliv-dev",
                                          queue="IndexQueue",
                                          exchange="IndexTask",
                                          routing_key="IndexTask",
                                          exchange_type="",
                                          log=mock.Mock())

    def test_removing_document(self):

        msg = Dict()
        msg.url = "http://example.com/home.html"
        msg.action = "delete"
        msg.document = {}

        with mock.patch("toddler.models.IndexDocument.objects") as objects:

            ob = objects.return_value
            delete = ob.delete
            delete.return_value = True
            self.index_manager.process_task(ujson.dumps(msg).encode("utf8"))

            self.assertTrue(delete.called)

    def test_upsert_document(self):

        msg = Dict()
        msg.url = "http://example.com/home.html"
        msg.action = "insert"
        msg.document = {
            "features": {
                "title": "test"
            },
            "meta_data": {
                "crawl_date": now() 
            }
        }

        with mock.patch("toddler.models.IndexDocument.objects") as objects:

            ob = objects.return_value
            update_one = ob.update_one
            update_one.return_value = True
            self.index_manager.process_task(ujson.dumps(msg).encode("utf8"))
            self.assertTrue(update_one.called)
            args, kwargs = update_one.call_args
            self.assertEqual(kwargs['set__features']['title'], "test")

