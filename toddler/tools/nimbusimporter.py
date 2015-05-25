__author__ = 'michal'
__version__ = "0.1.0"
from toddler.models import IndexDocument
from mongoengine import connect
from toddler.imports import nimbusview
import argparse
from toddler.logging import setup_logging


def main():
    """
    NimbusImporter v.0.1.0
    :return:
    """
    log = setup_logging()

    parser = argparse.ArgumentParser()

    parser.add_argument("-m", "--mongo-db", required=True,
                        help="MongoDB url to connect to: mongodb://localhost")
    parser.add_argument("-s", "--search-api", required=True,
                        help="Url of search api: http://10.10.105.104:10010/")

    parser.add_argument("-q", "--query", help="Query string")
    parser.add_argument("-l", "--search-logic", help="Search logic")
    parser.add_argument("-t", "--search-target", help="Search target")

    args = parser.parse_args()
    log.info("Connecting to mongodb %s", args.mongo_db)
    connect(host=args.mongo_db)
    log.info("Getting search results, and pushing them to MongoDB")
    [IndexDocument.upsert(d['url_hash'], d)
     for d in nimbusview.get_documents(args.search_api, {
        "query": args.query,
        "st": args.search_target,
        "sl": args.search_logic
     })]


if __name__ == '__main__':
    main()
