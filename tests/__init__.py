__author__ = 'michal'

from .config import ConfigTest
from .test_crawler import TestCrawler
from .rabbitmanager import TestRabbitManager
from .soup_contentprocessor import SoupContentProcessorTest
from .test_analyser import TestAnalyser
from .test_crawlmanager import CrawlManagerTests
from .test_exports import TestExports
from .test_indexmanager import IndexManagerTests


import unittest

if __name__ == '__main__':
    unittest.main()