__author__ = 'michal'

from unittest import TestCase, mock
from toddler.exceptions import NotConfigured
from functools import wraps


class _LogPatch(object):
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
            args = (_LogPatch(log), ) + args
            return func(self, *args, **kwargs)

    return wrapper


class TestRabbitManager(TestCase):

    @mock.patch("concurrent.futures.thread.ThreadPoolExecutor")
    @patch_logs
    def test_instantiation(self, log, executor):

        from toddler.managers import RabbitManager
        from concurrent.futures import Future

        ex_instance = executor.return_value
        future = Future()
        ex_instance.submit.return_value = future

        self.assertRaises(NotConfigured, RabbitManager, ("ampq://fliv", ))
        RabbitManager("ampq://fliv", "TestQueue")
        self.assertTrue(log._log.called)
        self.assertTrue(executor.called)
        log2 = mock.Mock()
        rm = RabbitManager("ampq://fliv", "TestQueue", log=log2)
        self.assertEqual(rm.log, log2)

    @mock.patch("toddler.logging.setup_logging")
    @mock.patch("toddler.managers.RabbitManager.requeue_message")
    @mock.patch("toddler.managers.RabbitManager.acknowledge_message")
    @mock.patch("concurrent.futures.ThreadPoolExecutor")
    @patch_logs
    def test_on_message(self, log, executor, ack_msg, req_msg):

        # TODO: testing of `RabbitManager.on_message`

        pass


