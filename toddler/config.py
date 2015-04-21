__author__ = 'michal'

import os
import ujson
import yaml

configs = {}


def read_config_file(file_path):

    with open(file_path, 'r') as file:
        if file_path.endswith(".yaml"):
            return yaml.load(file.read())
        else:
            return ujson.load(file)


def set_config(name, file_path):

    with open(file_path) as file:
        configs[name] = ujson.load(file)


def parse_config_dir(config_path):

    with open(os.path.join(config_path, 'toddler.conf')) as main_cfg_file:
        main = ujson.load(main_cfg_file)

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
