__author__ = 'michal'

from unittest import TestCase, mock
from mongomock import Connection
mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()

from toddler.models import CrawlDocument, hash_url, IndexDocument
from toddler import setup
from toddler.decorators import _reset_already_run

class TestModels(TestCase):

    def setUp(self):

        _reset_already_run(setup)

        setup(['-m', 'mongodb://localhost/aladdin'])

    def tearDown(self):

        _reset_already_run(setup)

    def test_crawl_document(self):

        cd = CrawlDocument(url="http://example.com", host="example.com")
        cd.save()
        self.assertEqual(cd.url_hash, hash_url(cd.url))

    def test_index_document(self):

        cd = IndexDocument(url="http://example.com", host="example.com")
        cd.save()
        self.assertEqual(cd.url_hash, hash_url(cd.url))
