__author__ = 'michal'

import unittest
import unittest.mock as mock
from toddler import crawler
import json
from datetime import datetime, timezone, timedelta


class Crawler(unittest.TestCase):
    
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
                self.assertEqual(d['cookies']['sessid'], "123")
                self.assertEqual(d['headers']['content-type'], "text/html")
