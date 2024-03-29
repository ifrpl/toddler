__author__ = 'michal'

from unittest import TestCase, mock
from toddler import Document, setup, config, _setup_run_already, decorators
import ujson
import tempfile
import os
from addict import Dict
import sys


class GeneralTests(TestCase):

    def tearDown(self):

        decorators._reset_already_run(setup)

    def test_setup(self):

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)\
                as tmp_file:

            tmp_file.write("test: 123")
            tmp_file.close()
            argv = ['-c', '{}'.format(tmp_file.name)]
            decorators._reset_already_run(setup)
            setup(argv)

            self.assertEqual(config.config.test, 123)
            os.unlink(tmp_file.name)

            self.assertRaises(SystemError, setup, argv)
            self.assertTrue(decorators.has_been_run(setup))

        config.config = Dict()

        decorators._reset_already_run(setup)

        # reset the already run
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) \
                as tmp_file:

            tmp_file.write('{"test": 123}')
            tmp_file.close()
            argv = ['-c', tmp_file.name]

            setup(argv)

            self.assertEqual(config.config.test, 123)

            os.unlink(tmp_file.name)

        decorators._reset_already_run(setup)

        argv = ['-m', "mongodb://localhost"]

        with mock.patch("toddler.models.connect") as connect:

            def mock_connect(host=None):
                self.assertEqual(host, "mongodb://localhost")
            connect.side_effect = mock_connect
            setup(argv)

            self.assertTrue(connect.called)

    def test_already_run(self):

        @decorators.run_only_once(True)  # should not raise exception
        def test():
            return 1

        self.assertEqual(test(), 1)
        self.assertEqual(test(), None)

        @decorators.run_only_once
        def test2():
            return 2

        self.assertEqual(test2(), 2)
        self.assertRaises(SystemError, test2)


    def test_document_object(self):

        d = Document()
        d.features = {
            "item1": "val1"
        }

        d.content = {
            "content1": "val1"
        }
        d.url = "http://example.com"

        json = d.toJSON()

        ob = ujson.loads(json)

        self.assertEqual(
            ob['features']['item1'],
            d.features['item1']
        )

        self.assertEqual(ob['url'], d.url)
        self.assertEqual(len(ob['content']), 1)

        self.assertEqual(str(d), d.toJSON())

        with mock.patch("ujson.dump") as dump:

            dump.return_value = None
            fp, fo = tempfile.mkstemp()

            d.toJSON(fp)

            self.assertEqual(fp, dump.call_args[0][0])
