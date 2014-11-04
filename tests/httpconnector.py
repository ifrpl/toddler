__author__ = 'michal'

import unittest
import asyncio
from toddler.crawler.connector.http import HttpConnector
from toddler import Document
import aiohttp
from aiohttp import server as aioserver
import time
import json

class TestServerHttpProtocol(aioserver.ServerHttpProtocol):

    def handle_request(self, message, payload):
        now = time.time()
        response = aiohttp.Response(
            self.writer, 404, http_version=message.version, close=True)


        body = """
            <!DOCTYPE html>
            <html>
                <head>
                    <title>Test Ad</title>
                </head>
                <body>
                    <div>Price <span>123€</span></div>
                </body>
            </html>
        """

        response.add_headers(
            ('CONTENT-TYPE', 'text/html'),
            ('CONTENT-LENGTH', str(len(body))))
        response.send_headers()
        response.write(body.encode("utf8"))
        drain = response.write_eof()

        self.keep_alive(False)
        self.log_access(message, None, response, time.time() - now)

        return drain

class HttpConnectorTest(unittest.TestCase):

    http_test_port = 8181

    def __init__(self, *args, **kwargs):

        super(HttpConnectorTest, self).__init__(*args, **kwargs)
        self.http_server = None
        """:type: asyncio.base_events.Server"""

    def setUp(self):

        loop = asyncio.get_event_loop()

        f = loop.create_server(
            lambda: TestServerHttpProtocol(),
            '127.0.0.1',
            self.http_test_port
        )

        self.http_server = loop.run_until_complete(f)
        """:type: asyncio.base_events.Server"""

    def testBroadcast(self):

        doc = Document()

        doc.url = "http://localhost:%d" % self.http_test_port

        content_extraction_config_json = """
        [ {
            "plugin": {
                "module":"toddler.contentprocessors.soup",
                "handler": "SoupContentProcessor"
            },
            "config": {
                "title": [
                    {
                        "command": "find",
                        "arguments": "title"
                    },
                    {
                        "command": "text"
                    }
                ]
            }
          }
        ]
        """

        httpconnector = HttpConnector(
            doc,
            {
                "contentExtractionConfig": json.loads(
                    content_extraction_config_json
                )
            }
        )

        loop = asyncio.get_event_loop()

        doc = loop.run_until_complete(httpconnector.work())
        """:type: Document"""
        self.assertEqual(doc.content['title'][0], "Test Ad")





    def tearDown(self):
        self.http_server.close()

