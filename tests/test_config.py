__author__ = 'michal'

from unittest import TestCase, mock
from mongomock import Connection

mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()

from toddler.models import Host, RobotsTxt
from toddler.config import push_configuration_for_host
from datetime import datetime, timezone, timedelta
from toddler import setup

class TestConfig(TestCase):

    def setUp(self):

        self.url_patterns = [
            {
                "patterns": [
                    "http:\/\/example.com\/.*\.html"
                ],
                "actions": ["follow", "index"]
            },
            {
                "patterns": [
                    "http:\/\/example.com\/nocrawl\/.*\.html"
                ],
                "actions": ["nofollow"]
            }
        ]
        host = {
            "host": "example.com",
            "block": False,
            "block_date": "2015-02-02T14:23:12+00:00",
            "number_of_documents": 3434,
            "config": {"crawlConfig": self.url_patterns},
            "ignore_robots": False,
            "robots_txt": RobotsTxt(**{
                "status": "downloaded",
                "status_code": 200,
                "content": "User-Agent: *\nAllow: /\n",
                "expires": datetime.now(timezone.utc)+timedelta(10)
            })
        }
        self.host = Host(**host)
        try:
            # we want to run it only once
            setup(['-m', 'mongodb://localhost'])
        except SystemError:
            # will raise exception because setup is run with every test
            pass


    @mock.patch("toddler.models.Host.objects")
    def test_config_insert_for_host(self, objects):

        inst = objects.return_value
        inst.first.return_value = self.host

        config = {
            "exports": {
                "nimbusview": {
                    "push_api_url": "http://test.api:2323"
                }
            }
        }

        push_configuration_for_host("example.com", config)

        self.assertEqual(len(self.host.config), 1)
        self.assertIn("exports", self.host.config)
        self.assertEqual(
            self.host.config['exports']['nimbusview']['push_api_url'],
            "http://test.api:2323"
        )


    @mock.patch("toddler.models.Host.objects")
    def test_config_insert_for_host_for_key(self, objects):

        inst = objects.return_value
        inst.first.return_value = self.host

        hostname = "example.com"
        config = [
            {
                "patterns": [
                    "http:\/\/example.com\/.*.php"
                ],
                "actions": ["follow", "noindex"]
            }
        ]

        push_configuration_for_host(hostname, config, "crawlConfig")
        self.assertIn("noindex",
                      self.host.config['crawlConfig'][0]["actions"])

    @mock.patch("toddler.models.Host.objects")
    def test_config_insert_for_host_for_nested_key(self, objects):

        host = self.host
        config = {
            "exports": {
                "nimbusview": {
                    "push_api_url": "http://test.api:2323"
                }
            }
        }
        host.config = config
        host.save()

        inst = objects.return_value
        inst.first.return_value = host

        hostname = "example.com"
        config = "http://test2.api:2323"

        push_configuration_for_host(hostname, config,
                                    "exports.nimbusview.push_api_url")

        self.assertEqual(host.config['exports']['nimbusview']['push_api_url'],
                         config)

    @mock.patch("toddler.models.Host.objects")
    def test_config_insert_for_host_for_nested_key_not_existing(self, objects):

        host = self.host
        config = {
            "exports": {
            }
        }
        host.config = config
        host.save()

        inst = objects.return_value
        inst.first.return_value = host

        hostname = "example.com"
        config = "http://test2.api:2323"

        push_configuration_for_host(hostname, config,
                                    "exports.nimbusview.push_api_url")

        self.assertEqual(host.config['exports']['nimbusview']['push_api_url'],
                         config)