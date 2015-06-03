__author__ = 'michal'
__version__ = "0.1.0"

import argparse
from toddler import setup
from colorama import Fore, Style

__all__ = ['main']

def main(*argv):
    """
    = Configuration import =

    check "--help"

    Run command: python -m toddler.tools.configimport

    :param argv:
    :return:
    """
    parser = argparse.ArgumentParser(
        argv,
        description="ConfigImport v{}".format(__version__)
    )

    parser.add_argument("-t", "--type", help="Config type",
                        choices=['crawl'])

    if len(argv) > 0:
        args = setup(argv, argument_parser=parser, do_not_parse_config=True)
    else:
        args = setup(argument_parser=parser, do_not_parse_config=True)

    print(Style.DIM + Fore.BLUE + "ConfigImport v{}".format(__version__))

    with open(args.config) as config_file:
        print(Fore.BLUE+"Opened file:"+Fore.RESET+" {}".format(args.config)
              + Fore.RESET)
        if args.type == "crawl":
            print(Style.BRIGHT+Fore.BLUE+"Importing crawlConfig")
            from toddler.imports.nimbuscrawl import get_configuration
            from toddler.models import Host
            config_content = config_file.read()
            config = get_configuration(config_content)
            for host_name, crawl_config in config:
                host = Host.objects(host=host_name).first()
                if host is None:
                    host = Host(host=host_name)

                host.config['crawlConfig'] = crawl_config
                host.save()
                print(Fore.GREEN + "+ Added config for host {}".format(
                    host_name))


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])