__author__ = 'michal'

import unittest
from unittest import mock
from mongomock import Connection

# mocking mongo connection
mongo_patcher = mock.patch("pymongo.MongoClient")
mock_mongo_client = mongo_patcher.start()
mock_mongo_client.return_value = Connection()

from toddler.managers.crawlmanager import *
from toddler.managers.crawlmanager import match_url_patterns
from bs4 import BeautifulSoup, Tag
import dateutil
from datetime import datetime, timezone, timedelta
import ujson
from toddler.models import Host, RobotsTxt, CrawlDocument, hash_url
from concurrent.futures import Future

def get_timeout(json):
    """
    Helper for parsing dates
    :param json:
    :return:
    """
    return dateutil.parser.parse(ujson.loads(json)['timeout'])


def declare_queue_side_effect(rabbitmq_url, queue_name):

    ftr = Future()

    ftr.set_result((queue_name, "{}_exchange".format(queue_name)))

    return ftr

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
        crawl_result.body = html
        crawl_result.cookies = {"sessid": "123123"}
        crawl_result.actions = ["follow", "index"]
        crawl_result.status_code = 200
        
        self.crawl_result = crawl_result
        
        self.crawl_manager = CrawlManager("mongodb://localhost/",
                                          rabbitmq_url="apmq://fliv-dev",
                                          queue="CrawlResultQueue",
                                          exchange="CrawlResult",
                                          routing_key="CrawlResult",
                                          exchange_type="",
                                          log=mock.Mock(),
                                          redis_url='localhost')



    # def tearDown(self):
    #
    #     self.mongo_patcher.stop()

    @property
    def host(self):

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

        return Host(**host)

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

    @mock.patch("toddler.models.Host.objects")
    def test_can_fetch_without_robots(self, objects):

        host = self.host
        inst = objects.return_value
        inst.first.return_value = host
        host.ignore_robots = True

        self.assertTrue(
            self.crawl_manager.can_fetch(host,
                                         "http://example.com/home.html")
        )

        host.ignore_robots = False
        host.robots_txt.status = "none"

        self.assertTrue(
            self.crawl_manager.can_fetch(host,
                                         "http://example.com/home.html")
        )

    def test_link_retrievals(self):
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
                        <a rel='next' href="/contact.html">Contact</a>
                    </li>
                    <li>
                        <a href="/ad.html" rel="nofollow">Cheap Watches</a>
                    </li>
                    <li>
                        <a href="#footer">internal</a>
                    </li>
                    <li>
                        <a href="/nocrawl/smth.html"></a>
                    <li>
                        <a href="http://otherhost.org/">External link</a>
                    </li>
                </ul>
            </div>
            <footer><a id="footer"></a></footer>
        </body>
    </html>
            """

        links = list(retrieve_links("http://example.com/home.html",
                                    BeautifulSoup(html)))

        self.assertEqual(5, len(links))

    @mock.patch("toddler.models.Host.objects")
    def test_crawl_requests_from_html(self, objects):
        
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

    @mock.patch("toddler.models.Host.objects")
    def test_crawl_requests_from_html_with_robots_disallow(self, objects):

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

    @mock.patch("toddler.models.Host.objects")
    def test_crawl_request_without_robots(self, objects):

        host = self.host
        host.robots_txt = RobotsTxt()
        inst = objects.return_value
        inst.first.return_value = host

        cm = self.crawl_manager

        def _raises():
            list(cm.extract_requests(self.crawl_result))

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

        html = """
        <html>
        <head>
            <meta name="encoding" content="utf8"/>
        </head>
        <body>
            <h1>Title</h1>
        </body>
        </html>"""
        # no robots indication and no noindex so `true`
        self.assertTrue(can_index_html(html, ""))

    @mock.patch("toddler.models.Host.objects")
    def test_crawl_request_with_robots_in_meta(self, objects):
        """
        Robots from html should override robots.txt
        :return:
        """
        host = self.host
        inst = objects.return_value
        inst.first.return_value = host

        crawl_result = self.crawl_result
        soup = BeautifulSoup(crawl_result.body)
        soup.find("head").append(
            Tag(builder=soup.builder, name="meta",
                attrs=dict(name="robots", content="NOINDEX, NOFOLLOW"))
        )

        crawl_result.body = soup.prettify("utf8")
        cm = self.crawl_manager

        self.assertEqual(
            len(list(cm.extract_requests(crawl_result))),
            0
        )

    @mock.patch("toddler.models.Host.objects")
    def test_should_crawl_request_be_indexed_with_robots_in_meta(self,
                                                                 objects):

        host = self.host
        inst = objects.return_value
        inst.first.return_value = host
        crawl_result = self.crawl_result
        soup = BeautifulSoup(crawl_result.body)

        soup.find("head").append(
            Tag(builder=soup.builder, name="meta",
                attrs=dict(name="robots", content="NOINDEX, NOFOLLOW"))
        )
        crawl_result.actions = ""
        crawl_result.body = soup.prettify("utf8")
        cm = self.crawl_manager
        self.assertFalse(cm.should_be_indexed(crawl_result))

    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.models.Host.objects")
    def test_should_reject_task_because_of_missing_robots(self, objects,
                                                          sync):
        host = self.host
        host.robots_txt = RobotsTxt()

        inst = objects.return_value
        inst.first.return_value = host

        cm = self.crawl_manager

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

    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.models.Host.objects")
    def test_should_reject_task_because_of_robots_expired(
            self, objects, sync):

        host = self.host
        host.robots_txt.expires = datetime.now(timezone.utc)-timedelta(10)
        inst = objects.return_value
        inst.first.return_value = host

        cm = self.crawl_manager

        self.assertRaises(
            RequeueMessage,
            cm.process_task,
            ujson.dumps(self.crawl_result.to_dict()).encode("utf8")
        )
        self.assertTrue(sync.called)
        args, kwargs = sync.call_args
        request = ujson.loads(args[1])
        self.assertTrue("robots" in request['actions'])

    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.models.Host.objects")
    def test_should_reject_task_because_of_robots_will_be_downloaded(
            self, objects, sync):

        host = self.host
        host.robots_txt.status = "waiting"
        inst = objects.return_value
        inst.first.return_value = host

        cm = self.crawl_manager

        self.assertRaises(
            RequeueMessage,
            cm.process_task,
            ujson.dumps(self.crawl_result.to_dict()).encode("utf8")
        )

    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.models.Host.objects")
    def test_should_create_analysis_request(self,
                                            objects, sync):

        inst = objects.return_value
        inst.first.return_value = self.host
            
        cm = self.crawl_manager
        cm.send_crawl_result_to_analysis(self.crawl_result)

        self.assertTrue(sync.called)
        args, kwargs = sync.call_args
        request = ujson.loads(args[1])

        self.assertEqual(request['url'], self.crawl_result.url)
        self.assertEqual(request['body'], self.crawl_result.body)

    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.models.Host.objects")
    def test_should_create_deletion_index_task(self, objects, sync):

        inst = objects.return_value
        inst.first.return_value = self.host

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

    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.managers.crawlmanager.declare_queue")
    @mock.patch("toddler.models.Host.objects")
    def test_should_create_crawl_requests(self, objects, declare_queue, sync):

        inst = objects.return_value
        inst.first.return_value = self.host

        cm = self.crawl_manager
        cm._crawl_request_delay = 10

        declare_queue.side_effect = declare_queue_side_effect

        cm.process_task(
            ujson.dumps(self.crawl_result.to_dict()).encode("utf8")
        )
        self.assertTrue(sync.called)
        # 1 analysis request and 3 crawl requests
        self.assertEqual(sync.call_count, 4)

    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.models.Host.objects")
    def test_process_robot_crawl_task(self, objects, sync):

        sync.return_value = True
        host = self.host
        inst = objects.return_value
        inst.first.return_value = host

        robots_response = {
            "url": "http://example.com/robots.txt",
            "body": "Allow: /",
            "actions": ["robots"],
            "status_code": 200,
            "headers": {
                "content-type": "text/html"
            },
            "crawl_time": datetime.now(timezone.utc).isoformat()
        }

        self.crawl_manager.process_task(
            ujson.dumps(robots_response).encode("utf8")
        )

        self.assertEqual(host.robots_txt.content, "Allow: /")

    @mock.patch("toddler.managers.crawlmanager.now")
    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.managers.crawlmanager.declare_queue")
    @mock.patch("toddler.models.Host.objects")
    def test_send_crawl_request(self, objects, declare_queue, sync, mock_now):

        request = Dict()
        request.url = "http://example.org/home.html"
        request.method = "GET"
        request.actions = ['follow', 'index']
        request.referer = ""
        request.cookies = {}

        host = self.host
        inst = objects.return_value
        inst.first.return_value = host

        test_now = datetime.now(timezone.utc)
        mock_now.return_value = test_now


        declare_queue.side_effect = declare_queue_side_effect

        self.crawl_manager.send_crawl_request(
            request.to_dict()
        )

        msg, *rest = sync.call_args
        doc = ujson.loads(msg[1])
        self.assertEqual(doc['url'], request.url)
        self.assertEqual(msg[3], 'CrawlRequestQueue_example.com_exchange')


    @mock.patch("toddler.models.CrawlDocument.objects")
    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    @mock.patch("toddler.managers.crawlmanager.declare_queue")
    @mock.patch("toddler.models.Host.objects")
    def test_status_codes_gt_200(self, objects, declare_queue, sync,
                                 cdobjects):


        inst = objects.return_value
        inst.first.return_value = self.host

        declare_queue.side_effect = declare_queue_side_effect

        crawl_response = {
            "url": "http://example.com/home.html",
            "body": "<html></html>",
            "actions": ["index"],
            "status_code": 500,
            "headers": {
                "content-type": "text/html"
            },
            "crawl_time": datetime.now(timezone.utc).isoformat()
        }

        now = datetime.now(timezone.utc)

        cd = CrawlDocument()
        cd.host = "example.com"
        cd.url = crawl_response['url']
        cd.url_hash = hash_url(crawl_response['url'])
        cd.latest_request = {
            "url": crawl_response['url'],
            "cookies": {},
            "method": "GET",
            "actions": ["follow", "index"]
        }
        cd.save()
        cinst = cdobjects.return_value
        cinst.first.return_value = cd

        self.crawl_manager.process_task(
            ujson.dumps(crawl_response).encode("utf8")
        )

        crawl_response['status_code'] = 302

        self.crawl_manager.process_task(
            ujson.dumps(crawl_response).encode("utf8")
        )

        self.assertEqual(sync.call_count, 2)


    @mock.patch("toddler.models.Host.objects")
    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    def test_should_requeue_host_blocked(self, sync, objects):

        host = self.host

        host.block = True
        inst = objects.return_value
        inst.first.return_value = host

        cm = self.crawl_manager

        self.assertRaises(
            RequeueMessage,
            cm.process_task,
            ujson.dumps(self.crawl_result.to_dict()).encode("utf8")
        )

    @mock.patch("toddler.models.Host.objects")
    @mock.patch("toddler.managers.crawlmanager.send_message_sync")
    def test_should_requeue_no_status_code(self, sync, objects):

        host = self.host

        inst = objects.return_value
        inst.first.return_value = host

        cm = self.crawl_manager

        crawl_result = self.crawl_result.to_dict()
        del crawl_result['status_code']
        self.assertRaises(
            RequeueMessage,
            cm.process_task,
            ujson.dumps(crawl_result).encode("utf8")
        )