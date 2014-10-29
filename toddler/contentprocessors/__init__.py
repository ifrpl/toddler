__author__ = 'michal'

from toddler import Document
from functools import reduce

class BaseContentProcessor(object):

    def __init__(self, config):
        self.config = config
        self._available_commands = ['join']
        self._setup()

    def _setup(self):
        pass

    def join(self, stream, *args):
        """
        Joins many pipe streams together

        Config example:
        {
           "command": "join",
            "arguments": [
                [
                    {
                        "command": "select",
                        "arguments": "td.f1"
                    },
                    {
                        "command": "text"
                    }
                ],
                [
                    {
                        "command": "select",
                        "arguments": "td.f3"
                    },
                    {
                        "command": "text"
                    }
                ],
                [
                    {
                        "command": "select",
                        "arguments": "td.f2"
                    },
                    {
                        "command": "text"
                    }
                ]
            ]
        }

        :param stream:
        :param args:
        :return list:
        """

        def generate(stream, args):
            for pipe in args:
                for r in reduce(self.parse_command, pipe, stream):
                    yield r

        return [element for element in generate(stream, args)]


    def parse_command(self, stream, options):
        """

        :param stream:
        :param options:
        :return: :raise NotImplementedError:
        """
        if type(stream) is not list:
            stream = [stream]

        def process_options(element):
            nonlocal options
            if "command" in options:
                if options['command'] in self._available_commands:
                    method = getattr(self, options['command'])
                else:
                    raise NotImplementedError(
                        "Command %s is not implemented, available: %s" %
                        (options['command'], str(self._available_commands)))
            else:
                raise TypeError("No command specified")

            args = [element]
            if 'arguments' in options:
                if type(options['arguments']) is not list:
                    args += [options['arguments']]
                else:
                    args += options['arguments']
            kwargs = {}
            if 'kw_arguments' in options:
                kwargs = options['kw_arguments']

            return method(*args, **kwargs)

        def iterate_stream(stream):

            for options in stream:
                result = process_options(options)
                if type(result) is list:
                    for r in result:
                        yield r
                else:
                    yield result

        return [element for element in iterate_stream(stream)]

    def get_stream(self, document: Document):
        return document.body

    def parse(self, document: Document):

        stream = self.get_stream(document)

        for element_name, pipe in self.config.items():
            elements = reduce(self.parse_command, pipe, stream)
            document.content[element_name] = elements
        return document
