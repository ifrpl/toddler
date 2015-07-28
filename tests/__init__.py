__author__ = 'michal'

from unittest import mock
from functools import wraps

import unittest


class LogPatch(object):
    """
    == Log Patcher ==
    Provides object with wrapped calls with mock for logging
    Example:

        @mock.patch("concurrent.futures.thread.ThreadPoolExecutor")
        @patch_logs
        def test_instantiation(self, log, executor):
            pass

    *Rember* that first argument will be log
    """
    def __init__(self, log):

        self._log = log
        log_inst = log.return_value
        self.exception = log_inst.exception
        self.exception.return_value = None
        self.info = log_inst.info
        self.info.return_value = None
        self.debug = log_inst.debug
        self.debug.return_value = None
        self.warning = log_inst.warning
        self.warning.return_value = None
        self.error = log_inst.error
        self.error.return_value = None


def patch_logs(func):

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with mock.patch("toddler.logging.setup_logging") as log:
            args = (LogPatch(log), ) + args
            return func(self, *args, **kwargs)

    return wrapper

if __name__ == '__main__':
    unittest.main()