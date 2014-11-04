import asyncio
from urllib.parse import urlsplit, SplitResult
from . import Connector
from http.cookies import SimpleCookie
import aiohttp
from aiohttp.client import ClientResponse
import dateutil.parser
from wsgiref.handlers import format_date_time
from time import mktime
from toddler.contentprocessors import parse_document
import copy
from functools import reduce

from toddler import Document

USER_AGENT = "Toddler 0.1 Crawling tool"

class HttpConnector(Connector):

    def __init__(self, document: Document, options, *args, **kwargs):
        """

        :param options:
        {
            "contentExtractionConfig": []
        }

        Document
         {
            "url": "http(s)://example.com",
            "meta": {
                "referer": "http(s)://example.com/ref",
                "cookies": {},
                "method": "GET" / "POST",
                "lastCrawlDate": "2014-10-25T21:25:10.893303'", // isoformat
                "remoteLastModified": "Sun, 06 Nov 1994 08:49:37 GMT", // http-date
            }
         }

        :param args:
        :param kwargs:
        :return:
        """

        super(HttpConnector, self).__init__(document, options, *args, **kwargs)

        self.connection = None
        """:type: asyncio.coroutine"""
        self.url = urlsplit(document.url)
        """:type: SplitResult"""


    @property
    def headers(self):

        base_headers = {
            "User-Agent": USER_AGENT,
        }

        if "remoteLastModified" in self.document.meta:

            base_headers['If-Modified-Since'] =\
                self.document["meta"]["remoteLastModified"]

        elif "lastCrawlDate" in self.document.meta:
            last_crawl_date = dateutil.parser.parse(
                self.document.meta['lastCrawlDate']
            )
            base_headers['If-Modified-Since'] =  format_date_time(
                mktime(last_crawl_date.timetuple())
            )

        return {}

    @property
    def cookies(self):
        if 'cookies' in self.document.meta:
            if self.document.meta['cookies'] is dict:
                return self.document.meta['cookies']
        return {}

    @asyncio.coroutine
    def work(self, future=None):

        if 'method' in self.options:
            method = self.options['method']
        else:
            method = "GET"

        response = yield from aiohttp.request(
            method,
            self.url.geturl(),
            headers=self.headers,
            cookies=self.cookies,
            allow_redirects=False
        )
        """:type: ClientResponse"""


        data = yield from response.text()

        doc = copy.copy(self.document)
        """:type: Document"""

        # doc.body = reduce(lambda x,y: x+y, iter(data), "")
        doc.body = data
        return parse_document(doc, self.options['contentExtractionConfig'])
