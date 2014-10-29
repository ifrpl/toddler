__author__ = 'michal'


from . import AbstractContentProcessor
from toddler import Document
from bs4 import BeautifulSoup
from functools import reduce

class SoupContentProcessor(AbstractContentProcessor):
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

    available_commands = ['findParents', 'select', 'find_previous_sibling',
                          'find_next_sibling', 'find', 'find_parents',
                          'find_parent']
    available_properties = ['text', 'parent']

    def select(self, soup: BeautifulSoup, select_string):
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

    def text(self, soup: BeautifulSoup):
        return soup.text
    def parent(self, soup: BeautifulSoup):
        return soup.parent

    def parse_command(self, soup, options):
        """

        :param soup:
        :param options:
        :return: :raise NotImplementedError:
        """
        if type(soup) is not list:
            soup = [soup]

        def process_options(tag):
            nonlocal options
            if "command" in options:
                if options['command'] in self.available_commands:
                    method = getattr(self, options['command'])
                else:
                    raise NotImplementedError
            elif "property" in options:
                method = getattr(self, options['property'])
            else:
                raise NotImplementedError

            args = [tag]
            if 'arguments' in options:
                if type(options['arguments']) is not list:
                    args += [options['arguments']]
                else:
                    args += options['arguments']
            kwargs = {}
            if 'kw_arguments' in options:
                kwargs = options['kw_arguments']

            return method(*args, **kwargs)

        def iterate_tags(tags):

            for tag in tags:
                result = process_options(tag)
                if type(result) is list:
                    for r in result:
                        yield r
                else:
                    yield result

        return [element for element in iterate_tags(soup)]


    def parse(self, document: Document):

        soup = BeautifulSoup(document.body)

        for element_name, pipe in self.config.items():
            elements = reduce(self.parse_command, pipe, soup)
            document.content[element_name] = elements
        return document