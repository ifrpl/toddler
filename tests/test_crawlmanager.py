__author__ = 'michal'

import unittest
from unittest import mock
from mongomock import Connection

mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()

from addict import Dict
from toddler.managers.crawlmanager import CrawlManager, NoRobotsForHostError,\
    can_fetch_url, can_index_html, RequeueMessage, has_robots_txt
from toddler.crawler import match_url_patterns
from bs4 import BeautifulSoup, Tag
import dateutil
from datetime import datetime, timezone, timedelta
import ujson
# mocking mongo connection
from toddler.models import Host, RobotsTxt


class CrawlManagerTests(unittest.TestCase):
    
    def setUp(self):

        # self.

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

        crawl_result = Dict()
        html = """
    <html>
        <head>
        </head>
        <body>
            <div class="navbar">
                <ul>
                    <li>
                        <a href="/index.html">Home</a>
                    </li>
                    <li>
                        <a href="/about.html">About</a>
                    </li>
                    <li>
                        <a href="/contact.html">Contact</a>
                    </li>
                    <li>
                        <a href="/ad.html" rel="nofollow">Cheap Watches</a>
                    </li>
                    <li>
                        <a href="/nocrawl/smth.html"></a>
                    <li>
                        <a href="http://otherhost.org/">External link</a>
                    </li>
                </ul>
            </div>
        </body>
    </html>
            """

        crawl_result.url = "http://example.com/home.html"
        crawl_result.html = html
        crawl_result.cookies = {"sessid": "123123"}
        crawl_result.actions = ["follow", "index"]
        crawl_result.status_code = 200
        
        self.crawl_result = crawl_result
        
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

        self.crawl_manager = CrawlManager("mongodb://localhost/",
                                          rabbitmq_url="apmq://fliv-dev",
                                          queue="CrawlResultQueue",
                                          exchange="CrawlResult",
                                          routing_key="CrawlResult",
                                          exchange_type="",
                                          log=mock.Mock())



    # def tearDown(self):
    #
    #     self.mongo_patcher.stop()

    def test_crawl_patterns(self):
        
        patterns = [
            {
                "patterns": [
                    "http:\/\/example.com\/.*\.html",
                    "http:\//\example.com\/index2\/[a-z0-9]+\.html"
                ],
                "actions": ["follow", "index"]
            },
            {
                "patterns": [
                    "http:\/\/example.com\/list\/.*",
                ],
                "actions": ["follow", "noindex"]
            },
            {
                "patterns": [
                    "http:\/\/example.com\/nocrawl\/.*.html"
                ],
                "actions": ["nofollow"]
            }
        ]
        
        urls = [
            ("http://example.com/index/123sde.html", ["follow", "index"]),
            ("http://example.com/index2/fff34.html", ["follow", "index"]),
            ("http://example.com/nocrawl/index.html", ["nofollow"]),
            ("http://example.com/list/p1", ["follow", "noindex"]),
            ("http://example.com/list/p2.html", ["follow", "noindex"]),
            ("http://example1.com/smth.html", [])
        ]
        
        for url, match in urls:
            self.assertListEqual(match, match_url_patterns(url, patterns))
    
    def test_crawl_requests_from_html(self):
        
        with mock.patch("toddler.models.Host.objects") as objects:

            inst = objects.return_value
            inst.first.return_value = self.host

            cm = self.crawl_manager

            crawl_requests = [url for url in cm.extract_requests(
                self.crawl_result)]
            
            self.assertEqual(len(crawl_requests), 3)
            
            for req in crawl_requests:
                a_req = Dict(req)
                self.assertDictEqual(a_req.cookies, self.crawl_result.cookies)
                self.assertEqual(a_req.method, "GET")
                
            self.crawl_result.actions = ["nofollow"]
            crawl_requests = [url for url in cm.extract_requests(
                self.crawl_result)]

            self.assertEqual(len(crawl_requests), 0)
            
    def test_crawl_requests_from_html_with_robots_disallow(self):

        with mock.patch("toddler.models.Host.objects") as objects:

            host = self.host
            
            host.robots_txt.content = """
            User-Agent: Toddler
            Disallow: /
            """

            inst = objects.return_value
            inst.first.return_value = host

            cm = self.crawl_manager

            crawl_requests = [url for url in cm.extract_requests(
                self.crawl_result)]

            self.assertEqual(len(crawl_requests), 0)

            host['user_agent'] = "Mozilla/5.0 (Windows NT 6.1)" \
                                " AppleWebKit/537.36 (KHTML, like Gecko) " \
                                "Chrome/41.0.2228.0 Safari/537.36"

            inst = objects.return_value
            inst.first.return_value = host

            cm = self.crawl_manager

            crawl_requests = [url for url in cm.extract_requests(
                self.crawl_result)]

            self.assertEqual(len(crawl_requests), 3)

    def test_crawl_request_without_robots(self):

        with mock.patch("toddler.models.Host.objects") as objects:

            host = self.host
            host.robots_txt = RobotsTxt()
            inst = objects.return_value
            inst.first.return_value = host

            cm = self.crawl_manager

            def _raises():
                requests = list(cm.extract_requests(self.crawl_result))

            self.assertRaises(NoRobotsForHostError, _raises)
            
    def test_can_index(self):
        
        actions = ["noindex", "follow"]
        html = """
        <html>
        <head>
            <meta name="robots" content="INDEX,FOLLOW"/>
        </head>
        <body>
            <h1>Title</h1>
        </body>
        </html>"""
        
        self.assertFalse(can_index_html(html, ",".join(actions)))
        
        actions = ["index", "follow"]
        html = """
        <html>
        <head>
            <meta name="robots" content="NOINDEX,FOLLOW"/>
        </head>
        <body>
            <h1>Title</h1>
        </body>
        </html>"""

        self.assertFalse(can_index_html(html, ",".join(actions)))

        actions = ["index", "follow"]
        html = """
        <html>
        <head>
            <meta name="robots" content="INDEX,FOLLOW"/>
        </head>
        <body>
            <h1>Title</h1>
        </body>
        </html>"""

        self.assertTrue(can_index_html(html, ",".join(actions)))

    def test_crawl_request_with_robots_in_meta(self):
        """
        Robots from html should override robots.txt
        :return:
        """
        with mock.patch("toddler.models.Host.objects") as objects:

            host = self.host
            inst = objects.return_value
            inst.first.return_value = host

            crawl_result = self.crawl_result
            soup = BeautifulSoup(crawl_result.html)
            soup.find("head").append(
                Tag(builder=soup.builder, name="meta",
                    attrs=dict(name="robots", content="NOINDEX, NOFOLLOW"))
            )
            
            crawl_result.html = soup.prettify("utf8")
            cm = self.crawl_manager
            
            self.assertEqual(
                len(list(cm.extract_requests(crawl_result))),
                0
            )

    def test_should_crawl_request_be_indexed_with_robots_in_meta(self):

        with mock.patch("toddler.models.Host.objects") as objects:

            host = self.host
            inst = objects.return_value
            inst.first.return_value = host
            crawl_result = self.crawl_result
            soup = BeautifulSoup(crawl_result.html)
        
            soup.find("head").append(
                Tag(builder=soup.builder, name="meta",
                    attrs=dict(name="robots", content="NOINDEX, NOFOLLOW"))
            )
            crawl_result.actions = ""
            crawl_result.html = soup.prettify("utf8")
            cm = self.crawl_manager
            self.assertFalse(cm.should_be_indexed(crawl_result))

    def test_should_reject_task_because_of_missing_robots(self):

        with mock.patch("toddler.models.Host.objects") as objects:

            host = self.host

            host.robots_txt = RobotsTxt()

            inst = objects.return_value
            inst.first.return_value = host

            cm = self.crawl_manager
            
            with mock.patch("toddler.managers.crawlmanager.send_message_sync")\
                    as sync:
                
                self.assertRaises(
                    RequeueMessage,
                    cm.process_task,
                    ujson.dumps(self.crawl_result.to_dict()).encode("utf8")
                )
                self.assertTrue(sync.called)
                args, kwargs = sync.call_args
                request = ujson.loads(args[1])
                self.assertTrue("robots" in request['actions'])
                
    def test_has_robots(self):

        self.assertTrue(has_robots_txt(self.host))
        host = self.host
        
        host.robots_txt.expires = datetime.now(timezone.utc)-timedelta(10)

        self.assertFalse(has_robots_txt(host))
        
        host.robots_txt = RobotsTxt()
        
        self.assertFalse(has_robots_txt(host))

                
    def test_should_reject_task_because_of_robots_expired(self):

        with mock.patch("toddler.models.Host.objects") as objects:

            host = self.host
            host.robots_txt.expires = datetime.now(timezone.utc)-timedelta(10)
            inst = objects.return_value
            inst.first.return_value = host

            cm = self.crawl_manager

            with mock.patch("toddler.managers.crawlmanager.send_message_sync") \
                    as sync:

                self.assertRaises(
                    RequeueMessage,
                    cm.process_task,
                    ujson.dumps(self.crawl_result.to_dict()).encode("utf8")
                )
                self.assertTrue(sync.called)
                args, kwargs = sync.call_args
                request = ujson.loads(args[1])
                self.assertTrue("robots" in request['actions'])

    def test_should_create_analysis_request(self):

        with mock.patch("toddler.models.Host.objects") as objects:

            inst = objects.return_value
            inst.first.return_value = self.host
            
            with mock.patch("toddler.managers.crawlmanager.send_message_sync") \
                as sync:
                
                cm = self.crawl_manager
                cm.send_crawl_result_to_analysis(self.crawl_result)
                
                self.assertTrue(sync.called)
                args, kwargs = sync.call_args
                request = ujson.loads(args[1])

                self.assertEqual(request['url'], self.crawl_result.url)
                self.assertEqual(request['html'], self.crawl_result.html)

    def test_should_create_deletion_index_task(self):

        with mock.patch("toddler.models.Host.objects") as objects:

            inst = objects.return_value
            inst.first.return_value = self.host

            with mock.patch("toddler.managers.crawlmanager.send_message_sync") \
                    as sync:

                cm = self.crawl_manager
                cr = self.crawl_result
                cr.status_code = 404
                cm.process_task(ujson.encode(cr).encode("utf8"))

                self.assertTrue(sync.called)
                args, kwargs = sync.call_args
                request = ujson.loads(args[1])
                self.assertEqual(args[2], "IndexTask")

                self.assertEqual(request['url'], self.crawl_result.url)
                self.assertEqual(request['action'], "delete")


    def test_should_create_crawl_requests(self):

        with mock.patch("toddler.models.Host.objects") as objects:

            inst = objects.return_value
            inst.first.return_value = self.host

            with mock.patch("toddler.managers.crawlmanager.send_message_sync") \
                    as sync:
            
                cm = self.crawl_manager
                cm._crawl_request_delay = 10

                cm.process_task(
                    ujson.dumps(self.crawl_result.to_dict()).encode("utf8")
                )
                self.assertTrue(sync.called)
                # 1 analysis request and 3 crawl requests
                self.assertEqual(sync.call_count, 4)

                first_call = sync.call_args_list[0][0]
                second_call = sync.call_args_list[1][0]

                def get_timeout(json):
                    return dateutil.parser.parse(ujson.loads(json)['timeout'])

                t1 = get_timeout(first_call[1])
                t2 = get_timeout(second_call[1])
                self.assertTrue(t2-t1 == timedelta(seconds=10))