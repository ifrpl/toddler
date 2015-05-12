__author__ = 'michal'

import ujson
import os
import logging
import logging.config
import inspect
import yaml


default_logging_conf = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
            },
        },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}


def setup_logging(logger=None, logger_name=None, config="logging.json",
                  env_key="TODDLER_LOGGING_CONF"):
    """
    === Logger setup ===

    Configure logging in two ways
    - Pass logger directly
    - Or pass config file in json or yaml, config file should be formatted
    according to (this documentation)[https://docs.python.org/3.4/library/logging.config.html#configuration-dictionary-schema]

    Sets up logging for this process
    :param logger: optional logger that will be used by manager
    :param logger_name: name of the logger
    :param config: configuration for the logger @see logging.config.dictConfig

    :return logging.Logger:
    """

    if logger is None:

        config = os.getenv(env_key, config)

        try:
            try:
                with open(config, 'r') as config_file:
                    if config.endswith(".json"):
                        config = ujson.load(config_file)
                    elif config.endswith(".yaml"):
                        config = yaml.load(config_file.read())
            except TypeError:
                if isinstance(config, dict):
                    config = config
            except (FileNotFoundError, IOError):
                config = default_logging_conf

            logging.config.dictConfig(config)
            log = logging.getLogger(logger_name)
        except KeyError:
            logging.warning(
                "Logging not configured for %s" % logger_name
            )
            frame = inspect.currentframe()
            try:
                next_frame = inspect.getouterframes(frame)[1]
                frame_info = inspect.getframeinfo(next_frame)
                logger_name = "Log:%s:%s" % (
                    frame_info.filename,
                    frame_info.function
                )
            finally:
                del frame
            log = logging.getLogger(logger_name or "NotConfiguredLog")
            log.setLevel(logging.DEBUG)

    else:
        log = logger

    return log