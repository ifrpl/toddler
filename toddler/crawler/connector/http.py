import asyncio
from urllib.parse import urlsplit, SplitResult
from . import Connector
from http.cookies import SimpleCookie
import aiohttp
from aiohttp.client import ClientResponse
import dateutil.parser
from wsgiref.handlers import format_date_time
from time import mktime

USER_AGENT = "Toddler 0.1 Crawling tool"

class HttpConnector(Connector):

    def __init__(self, options, *args, **kwargs):
        """

        :param options:

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
        self.connection = None
        """:type: asyncio.coroutine"""
        self.url = urlsplit(options['url'])
        """:type: SplitResult"""
        
        super(HttpConnector, self).__init__(options, *args, **kwargs)

    @property
    def headers(self):

        base_headers = {
            "User-Agent": USER_AGENT,
        }

        if "remoteLastModified" in self.options['meta']:

            base_headers['If-Modified-Since'] =\
                self.options["meta"]["remoteLastModified"]

        elif "lastCrawlDate" in self.options['meta']:
            last_crawl_date = dateutil.parser.parse(
                self.options['meta']['lastCrawlDate']
            )
            base_headers['If-Modified-Since'] =  format_date_time(
                mktime(last_crawl_date.timetuple())
            )

        return {}

    @property
    def cookies(self):
        if 'cookies' in self.options['meta']:
            if self.options['meta']['cookies'] is dict:
                return self.options['meta']['cookies']
        return {}

    @asyncio.coroutine
    def work(self):

        if 'method' in self.options['meta']:
            method = self.options['meta']['method']
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

        data = response.text()


