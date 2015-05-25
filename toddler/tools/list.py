__author__ = 'michal'
import os
from toddler import setup
from argparse import ArgumentParser
from glob import glob
import importlib.machinery
from colorama import Fore, Style

def main(*argv):
    """
    = Toddler tools list v0.1.0
    :param argv:
    :return:
    """

    parser = ArgumentParser(usage="--list",
                            description="Returns list of available tools")

    parser.add_argument("-l", "--list", default=True, action="store_true")
    parser.add_argument("-r", "--raw", default=False, action="store_true")
    args = setup(argv, argument_parser=parser, do_not_parse_config=True)

    if args.list:
        if not args.raw:
            print()
            name = "Toddler tools lister."
            print(Style.BRIGHT+Fore.BLUE+name)
            print(Style.DIM+Fore.BLUE+"="*len(name))
            print()
            print(Fore.YELLOW+"Usage: toddler-tools "+Style.DIM+"TOOL_NAME")
            print()
            print("Available tools:")
        for fname in glob(os.path.join(os.path.dirname(__file__), "*.py")):
            base_fname = os.path.basename(fname).replace(".py", "")
            if base_fname != "__init__":
                loader = importlib.machinery.SourceFileLoader(
                    "toddler.tools."+base_fname,
                    fname
                )
                im = loader.load_module()
                if hasattr(im, 'main'):
                    if not args.raw:
                        print(Fore.GREEN+"\t{}".format(base_fname))
                    else:
                        print(base_fname)
        if not args.raw:
            print("\nCheck " + Fore.RED + ""
                  "--help" + Fore.RESET + " for each one of them for more"
                                          " information\n")

if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
