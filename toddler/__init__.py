__author__ = 'michal'
__version__ = "0.1.0"

import ujson as json
from . import utils
from .rabbit_sender import send_message_sync


class Document(object):
    """
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
    """
    def __init__(self, source_dict=None):
        self.url = None
        self.meta = {}
        self.body = ""
        self.content = {}
        self.features = {}

        if source_dict is not None:
            self.load(source_dict)

    def toJSON(self, fp=None):

        d = {}
        d['url'] = self.url
        d['meta'] = self.meta
        d['body'] = self.body
        d['content'] = self.content
        d['features'] = self.features

        if fp is not None:
            json.dump(fp)
            return True
        else:
            return json.dumps(d)

    def __str__(self):
        return self.toJSON()

    def load(self, source_dict):

        for key in ['url', 'meta', 'features', 'content', 'body']:
            if key in source_dict:
                setattr(self, key, source_dict[key])

