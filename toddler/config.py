__author__ = 'michal'

import json
import os


configs = {}


def set_config(name, file_path):

    with open(file_path) as file:
        configs[name] = json.load(file)


def parse_config_dir(config_path):

    with open(os.path.join(config_path, 'toddler.conf')) as main_cfg_file:
        main = json.load(main_cfg_file)

        try:
            for name, val in main.items():
                # supporting includes
                if name == "includes":
                    [set_config(name, os.path.join(config_path, val))
                     for name, val in main['includes'].items()]
                else:
                    configs[name] = val

        finally:
            pass
