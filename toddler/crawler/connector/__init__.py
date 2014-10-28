__author__ = 'michal'

import asyncio


class Connector(object):

    def __init__(self, options, *args, **kwargs):
        """

        :param options:
        :param args:
        :param kwargs:
        :return:
        """

        self.options = options

    @asyncio.coroutine
    def work(self):
        raise NotImplementedError
