__author__ = 'michal'

from unittest import TestCase, mock
from toddler.exceptions import NotConfigured
from functools import wraps
from . import LogPatch, patch_logs


class TestRabbitManager(TestCase):

    @mock.patch("toddler.managers.ThreadPoolExecutor")
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

    @mock.patch("toddler.managers.RabbitManager.requeue_message")
    @mock.patch("toddler.managers.RabbitManager.acknowledge_message")
    @mock.patch("concurrent.futures.ThreadPoolExecutor")
    @patch_logs
    def test_on_message(self, log, executor, ack_msg, req_msg):

        # TODO: testing of `RabbitManager.on_message`

        pass


