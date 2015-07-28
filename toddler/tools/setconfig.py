__author__ = 'michal'
__version__ = "0.1"
import sys
import argparse
from colorama import Fore
from ..models import Host


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

    parser.add_argument("-o", "--host", help="Hostname to push config or many"
                                             " hostnames separated by `,` or"
                                             " `-` to read list from stdin or "
                                             " path to file with hostnames",
                        required=False)
    parser.add_argument("-k", "--key", help="Config key", required=False)
    parser.add_argument("-v", "--value", type=str)
    parser.add_argument("-f", "--file", help="file with config")
    parser.add_argument("-l", "--list-hosts", help="lists hosts line by line",
                        action="store_true")

    from ..config import push_configuration_for_host, read_config_file
    from .. import setup

    args = setup(argv, parser, do_not_parse_config=True)

    if args.list_hosts:
        for host in Host.objects:
            print(host.host)
        sys.exit(1)

    from mongoengine.errors import DoesNotExist
    import os

    if "," in args.host:
        hosts = [name.strip() for name in args.host.split(",")]
    else:
        if args.host.strip() == '-':
            hosts = [name.strip() for name in sys.stdin.readlines()]
        else:
            if os.path.exists(args.host):
                with open(args.host) as host_list_file:
                    hosts = [name.strip()
                             for name in host_list_file.readlines()]
            else:
                hosts = (args.host, )

    if args.value is None and args.file is None:
        for hostname in hosts:
            try:
                host = Host.objects(host=hostname.strip()).first()
                if host is None:
                    raise DoesNotExist
                print(host.host)

                def _get_config(config, keys):
                    if len(keys) == 1:
                        return config[keys[0]]
                    else:
                        return _get_config(config[keys[0]], keys[1:])
                try:
                    import json
                    print(json.dumps(_get_config(host.config,
                                                  args.key.split(".")),
                                      indent=4))
                except KeyError:
                    print(Fore.RED + "Cannot find key {}".format(args.key))
            except DoesNotExist:
                print(Fore.RED + "Cannot find host {}".format(hostname))
        sys.exit(0)

    if args.file:
        try:
            value = read_config_file(args.file)
        except IOError:
            print(Fore.RED + "Cannot open file {}".format(args.file))
            sys.exit(1)
    else:
        value = args.value
    try:
        [push_configuration_for_host(host.strip(), value, args.key)
         for host in hosts]
    except DoesNotExist:
        print(Fore.RED + "Host {} does not exist".format(args.host))
        sys.exit(1)

if __name__ == '__main__':
    main(*sys.argv[1:])