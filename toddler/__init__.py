__author__ = 'michal'
__version__ = "0.0.1"

import ujson as json
from . import utils
from .rabbit_sender import send_message_sync
from . import config

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


_setup_run_already = False

from .decorators import run_only_once
import argparse

@run_only_once
def setup(args=list(), argument_parser: argparse.ArgumentParser=None,
          do_not_parse_config=False):
    """
    = Setup =

    Basic setup of the application
    * connect to MongoDb if url given
    * configuration parsing json or yaml

    This function can be run only once, otherwise will raise an exception

    Returns processed args

    :return argparse.NameSpace:
    """
    global _setup_run_already


    if argument_parser is None:
        parser = argparse.ArgumentParser()
    else:
        parser = argument_parser

    try:
        parser.add_argument("-c", "--config",
                            help="Path to configuration file")
    except argparse.ArgumentError:
        pass

    parser.add_argument("--no-color", default=False, action="store_true",
                        help="Disable colors")


    try:
        parser.add_argument("-m", "--mongo-url", help="url to mongodb")
    except argparse.ArgumentParser:
        pass

    if len(args) > 0:
        parsed_args = parser.parse_args(args)
    else:
        parsed_args = parser.parse_args()

    if not parsed_args.no_color:
        from colorama import init
        init(autoreset=True)


    if parsed_args.config and not do_not_parse_config:

        from .logging import setup_logging
        log = setup_logging()

        log.info(
            "Parsing configuration in file: {}".format(parsed_args.config)
        )
        config.config = config.read_config_file(parsed_args.config)

    if parsed_args.mongo_url:

        from .models import connect

        connect(host=parsed_args.mongo_url)

    return parsed_args
