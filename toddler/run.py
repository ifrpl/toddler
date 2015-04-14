__author__ = 'michal'

from .managers import crawlmanager, indexmanager
from .crawler import Crawler
from .analyser import Analyser
from .config import read_config_file
import argparse
import argparse
import sys

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--process", help="Process name")
    parser.add_argument("-l", "--list", help="List processes"),
    parser.add_argument("-c", "--config", help="Config file for process")

    processes = {
        "Crawler": Crawler,
        "Analyser": Analyser,
        "CrawlManager": crawlmanager.CrawlManager,
        "IndexManager": indexmanager.IndexManager
    }

    args = parser.parse_args()

    try:
        process = processes[args.process]
        try:
            config = read_config_file(args.config)
        except IOError as e:
            print("Cannot read configuration file `%s`" % args.config,
                  file=sys.stderr)
            raise SystemError

        with process(**config) as instance:
            try:
                instance.run()
            except KeyboardInterrupt:
                instance.stop()

    except KeyError:
        print("Process %s not found", file=sys.stderr)
        sys.exit(1)
    except SystemError:
        sys.exit(1)



