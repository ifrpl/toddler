__author__ = 'michal'

import os
import ujson
import yaml
from addict import Dict

configs = {}
config = Dict()


def read_config_file(file_path):

    with open(file_path, 'r') as file:
        if file_path.endswith(".yaml"):
            return Dict(yaml.load(file.read()))
        else:
            return Dict(ujson.load(file))


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


def push_configuration_for_host(host, config, key=None):

    from .models import Host

    host = Host.objects(host=host).first()

    if key is None:
        host.config = config
    else:
        if "." not in key:
            host.config[key] = config
        else:
            keys = key.split('.')

            def _set_config(config, keys, value):
                if len(keys) == 1:
                    config[keys[0]] = value
                else:
                    try:
                        _set_config(config[keys[0]], keys[1:], value)
                    except KeyError:
                        # we still have keys, so create a dict and move further
                        config[keys[0]] = {}
                        _set_config(config[keys[0]], keys[1:], value)

            _set_config(host.config, keys, config)

    host.save()

