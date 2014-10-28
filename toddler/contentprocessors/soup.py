__author__ = 'michal'

from . import AbstractContentProcessor
from toddler import Document
from bs4 import BeautifulSoup

class SoupContentProcessor(AbstractContentProcessor):
    """
    config
        {
            "title": {
                "command": "select",
                "arguments": [
                    "h1"
                ],
                "subCommand": {
                    "property": "text"
                }
            },
            "price": {
                "command": "select",
                "arguments": [
                    "span.price"
                ],
                "subCommand": {
                    "command": "findParents",
                    "arguments": [
                        "div"
                    ],
                    "kw_arguments": {
                        "class": "col"
                    }
                }
            }
        }
    """

    available_commands = ['findParents']
    available_properties = ['text', 'parent']

    def text(self, soup: BeautifulSoup, select: str):
        return [el.text for el in soup.select(select)]

    def parent(self, soup: BeautifulSoup, options):
        pass

    def parse_command(self, soup, options):

        if "command" in options:
            if options['command'] in self.available_commands:
                method = getattr(self, options['command'])
            else:
                raise NotImplementedError

        elif "property" in options:
            method = getattr(self, options['property'])

        args = []
        if 'arguments' in options:
            args = options['arguments']
        kwargs = {}
        if 'kw_arguments' in options:
            kwargs = options['kw_arguments']

        elements = [el for el in method(*args, **kwargs)]

        if "subCommand" in options:
            return [self.parse_command(el, options['subCommand']) for el in elements]
        else:
            return elements


    def parse(self, document: Document):

        soup = BeautifulSoup(document.body)

        for element_name, expression in self.config.items():

            if expression is str:
                document.content[element_name] = self.text(soup, expression)
            else:
                pass
        return document