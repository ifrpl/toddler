__author__ = 'michal'


from . import BaseContentProcessor
from toddler import Document
from bs4 import BeautifulSoup
from functools import reduce

class SoupContentProcessor(BaseContentProcessor):
    """
    config
        {
            "title":
                {
                    "command": "select",
                    "arguments": [
                        "h1"
                    ]
                },
                {
                    "property": "text"
                }
            },
            "price": [
                {
                    "command": "select",
                    "arguments": [
                        "span.price"
                    ]
                },
                {
                    "command": "findParents",
                    "arguments": [
                        "div"
                    ],
                    "kw_arguments": {
                        "class": "col"
                    }
                }
            ]
        }
    """

    def _setup(self):
        super(SoupContentProcessor, self)._setup()
        
        available_commands = ['findParents', 'select', 'find_previous_sibling',
                              'find_next_sibling', 'find', 'find_parents',
                              'find_parent', 'text', 'parent', 'get_attribute']

        self._available_commands += available_commands



    def select(self, soup: BeautifulSoup, select_string):
        if isinstance(select_string, list):
            select_string = select_string.pop()
        return soup.select(select_string)

    def find_previous_sibling(self, soup: BeautifulSoup, *args, **kwargs):
        return soup.find_previous_sibling(*args, **kwargs)

    def find_next_sibling(self, soup: BeautifulSoup, *args, **kwargs):
        return soup.find_next_sibling(*args, **kwargs)

    def find(self, soup: BeautifulSoup, *args, **kwargs):
        return soup.find(*args, **kwargs)

    def find_parents(self, soup: BeautifulSoup, *args, **kwargs):
        return soup.find_parents(soup, *args, **kwargs)

    def find_parent(self, soup: BeautifulSoup, *args, **kwargs):
        return soup.find_parent(soup, *args, **kwargs)

    def get_attribute(self, soup: BeautifulSoup, attr_name):
        try:
            return soup.__getitem__(attr_name)
        except KeyError:
            return None

    def text(self, soup: BeautifulSoup):
        return soup.text

    def parent(self, soup: BeautifulSoup):
        return soup.parent

    def get_stream(self, document: Document):
        return BeautifulSoup(document.body)

