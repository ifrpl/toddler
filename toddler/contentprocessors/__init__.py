__author__ = 'michal'

from toddler import Document

class AbstractContentProcessor(object):

    def __init__(self, config):
        self.config = config

    def process(self, document: Document):
        """
        :param data:
        :type data: Document
        :return Document:
        """
        return document
