__author__ = 'michal'

import sys
import argparse
from colorama import Fore
from ..models import Host, CrawlDocument
from ..analyser import Analyser
from .. import setup
import ujson


def main(*args, **kwargs):

    parser = argparse.ArgumentParser("PushDocument")

    parser.add_argument("-f", "--file", help="JSON file with crawl result")
    parser.add_argument("-s", "--hash", help="Document hash")
    parser.add_argument("-u", "--url", help="Document url")
    parser.add_argument("-o", "--connector", help="force connector")
    parser.add_argument("-p", "--papi", help="Url to push api", required=True)
    options = setup(args, argument_parser=parser)

    if options.file is not None:
        with open(options.file) as json_file:
            crawled_document = ujson.load(json_file)

    elif options.hash is not None:
        cd = CrawlDocument.objects(url_hash=options.hash).first()
        crawled_document = cd.latest_result
    elif options.url is not None:
        cd = CrawlDocument.objects(url=options.url).first()
        crawled_document = cd.latest_result
    else:
        print(Fore.RED, "Please provide at least one option: `file`, `hash`"
                        " or `url`")
        sys.exit(1)

    analyser = Analyser(options.mongo_url, rabbitmq_url="", queue="")

    # build analyser request

    if 'latest_result' in crawled_document:
        crawled_document = crawled_document['latest_result']

    msg = ujson.dumps(crawled_document)

    analyser.process_task(msg.encode("utf8"), options.papi, options.connector)

    print(Fore.GREEN, "Message sent to analysis")


if __name__ == '__main__':

    main(*sys.argv[1:])