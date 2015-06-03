__author__ = 'michal'
__version__ = "0.1"
import sys
import argparse
from colorama import Fore


def main(*argv):
    """
    Config pusher for hosts

    """
    usage = """
    Provide file or value directly to change the value on host
    """

    parser = argparse.ArgumentParser(
        argv,
        description="SetConfig v{}".format(__version__),
        usage=usage
    )

    parser.add_argument("-o", "--host", help="Hostname to push config",
                        required=True)
    parser.add_argument("-k", "--key", help="Config key", required=True)
    parser.add_argument("value", type=str)
    parser.add_argument("-f", "--file", help="file with config")

    from ..config import push_configuration_for_host, read_config_file
    from .. import setup

    args = setup(argv, parser, do_not_parse_config=True)

    if args.file is None and args.value is None:
        print(Fore.RED + "Please provide file or value")
        sys.exit(1)

    if args.file:
        try:
            value = read_config_file(args.file)
        except IOError:
            print(Fore.RED + "Cannot open file {}".format(args.file))
            sys.exit(1)
    else:
        value = args.value

    from mongoengine.errors import DoesNotExist

    try:
        push_configuration_for_host(args.host, value, args.key)
    except DoesNotExist:
        print(Fore.RED + "Host {} does not exist".format(args.host))
        sys.exit(1)

if __name__ == '__main__':
    main(*sys.argv[1:])