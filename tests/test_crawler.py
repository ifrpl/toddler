__author__ = 'michal'

import unittest
import unittest.mock as mock
from toddler import crawler
import json
from datetime import datetime, timezone, timedelta
from tests import LogPatch, patch_logs
from concurrent.futures import Future


class TestCrawler(unittest.TestCase):

    @patch_logs
    def test_crawler_listener(self, log):

        future = Future()

        listener = crawler.CrawlerRedisListener("localhost",
                                                ['crawl_start', 'crawl_end'],
                                                log=log,
                                                promise=future)

        item_start = {
            'channel': b'crawl:start',
            'data': b'2015-06-08T18:18:02.854905+00:00\0http://example.com/test/ad.html'
        }

        listener.work(item_start)

        self.assertTrue(listener.host_is_being_crawled(
            "http://example.com/test-r.html"
        ))

        item_end = {
            'channel': b'crawl:stop',
            'data': b'2015-06-08T18:18:02.854905+00:00\0http://example.com/test/ad.html'
        }

        listener.work(item_end)

        self.assertFalse(listener.host_is_being_crawled(
            "http://example.com/test-r.html"
        ))

        listener.work(item_start)
        self.assertTrue(listener.host_is_being_crawled(
            "http://example.com/test-r.html"
        ))

        listener.work(item_start)
        self.assertTrue(listener.host_is_being_crawled(
            "http://example.com/test-r.html"
        ))

        listener.work(item_end)

        self.assertTrue(listener.host_is_being_crawled(
            "http://example.com/test-r.html"
        ))

        listener.work(item_end)

        self.assertFalse(listener.host_is_being_crawled(
            "http://example.com/test-r.html"
        ))

    @mock.patch("toddler.crawler.Crawler.connect")
    @mock.patch("toddler.rabbit_sender.declare_queue")
    def test_queue_declaration(self, declare_queue, connect):

        connection = connect.return_value
        channel = connection.channel.return_value
        consume = channel.consume

        c = crawler.Crawler()

        c.listener.hosts.append("www.example.com")

        def consume_side_effect(queue):
            nonlocal self
            self.assertEqual(queue, "CrawlRequestQueue_www.example.com")
            c.stop()
            return []
        consume.side_effect = consume_side_effect

        c.run()


    def test_crawler(self):

        m = mock.MagicMock()

        with mock.patch("requests.Session", m) as SessionMock:

            html = """<html></html>"""
            instance = SessionMock.return_value
            req = instance.get.return_value
            req.text = html
            req.cookies.get_dict.return_value = {"sessid": "123"}
            req.headers = {
                'content-length': len(html),
                'content-type': 'text/html'
            }

            with mock.patch("toddler.send_message_sync",
                            mock.Mock()) as sync:

                sync.return_value = None
                c = crawler.Crawler(rabbitmq_url="amqp://webapp:webapp@fliv-dev/",
                                    queue="",
                                    exchange="",
                                    routing_key="",
                                    exchange_type="",
                                    log=mock.Mock()
                                    )

                self.assertRaises(
                    crawler.RequeueMessage,
                    c.process_task,
                    ("""
                    {
                        "url": "http://immobilier.flivistic.fr",
                        "referer": "http://flivistic.fr",
                        "method": "GET",
                        "timeout": "%s"
                    }
                    """ % (
                        timedelta(10)+datetime.now(timezone.utc)
                    ).isoformat()).encode("utf8"))


                c.process_task("""{
                    "url": "http://immobilier.flivistic.fr",
                    "referer": "http://flivistic.fr",
                    "method": "GET"
                }""".encode("utf8"))

                self.assertTrue(sync.called)
                args, kwargs = sync.call_args
                d = json.loads(args[1])
                self.assertEqual(d['body'], html)

                cookies = {}
                [cookies.__setitem__(key, val) for key, val in d['cookies']]

                self.assertEqual(cookies['sessid'], "123")
                self.assertEqual(d['headers']['content-type'], "text/html")
