__author__ = 'michal'

import asyncio
from toddler import Document


class Connector(object):

    def __init__(self, document: Document, options, *args, **kwargs):
        """

        :param options:
        :param args:
        :param kwargs:
        :return:
        """

        self.options = options
        self.document = document

    @asyncio.coroutine
    def work(self):
        raise NotImplementedError
