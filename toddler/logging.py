__author__ = 'michal'

import logging
import logging.config
import inspect


def setup_logging(logger=None, logger_name=None, config=None):
    """
    Sets up logging for this process
    :param logger: optional logger that will be used by manager
    :param logger_name: name of the logger
    :param config: configuration for the logger @see logging.config.dictConfig
     https://docs.python.org/3.4/library/logging.config.html#configuration-dictionary-schema
    :return logging.Logger:
    """

    if logger is None:

        try:
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