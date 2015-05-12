__author__ = 'michal'

from .managers import crawlmanager, indexmanager
from .crawler import Crawler
from .analyser import Analyser
from . import config
from . import setup
import argparse
import sys
import colorama
colorama.init(True)

try:
    import colored_traceback
    colored_traceback.add_hook(True)
except ImportError:
    pass

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument("-p", "--process")
    parser.add_argument("-l", "--list", help="List processes",
                        action="store_true"),
    parser.add_argument("-c", "--config", help="Config file for process")

    processes = {
        "Crawler": Crawler,
        "Analyser": Analyser,
        "CrawlManager": crawlmanager.CrawlManager,
        "IndexManager": indexmanager.IndexManager
    }

    args = setup(argument_parser=parser)

    if args.process is None and args.list is False:
        parser.error(colorama.Fore.RED+"--process or --list is required")
        sys.exit(1)

    if args.list:
        print("Available processes:")
        [print("\t", k) for k, v in processes.items()]
        sys.exit(0)

    try:
        process = processes[args.process]

        with process(**dict(config.config)) as instance:
            try:
                instance.run()
            except KeyboardInterrupt:
                pass

    except KeyError:
        print("Process %s not found" % args.process, file=sys.stderr)
        sys.exit(1)
    except SystemError:
        sys.exit(1)
    except Exception as e:
        from .logging import setup_logging
        log = setup_logging()
        log.exception("Quit with exception", e)
        raise e
        sys.exit(1)
