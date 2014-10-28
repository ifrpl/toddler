__author__ = 'michal'

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

    def load(self, source_dict):

        for key in ['url', 'meta', 'features', 'content', 'body']:
            if key in source_dict:
                setattr(self, key, source_dict[key])
