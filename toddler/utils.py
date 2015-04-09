__author__ = 'michal'
import asyncio


def un_camel(text):
    """ Converts a CamelCase name into an under_score name.

        >>> un_camel('CamelCase')
        'camel_case'
        >>> un_camel('getHTTPResponseCode')
        'get_http_response_code'
    """
    result = []
    pos = 0
    while pos < len(text):
        if text[pos].isupper():
            if pos-1 > 0 and text[pos-1].islower() or pos-1 > 0 and \
                                    pos+1 < len(text) and text[pos+1].islower():
                result.append("_%s" % text[pos].lower())
            else:
                result.append(text[pos].lower())
        else:
            result.append(text[pos])
        pos += 1
    return "".join(result)


def run_process(*args, **kwargs):

    class TestProtocol(asyncio.SubprocessProtocol):

        def __init__(self, exit_future: asyncio.Future,
                     enough_data_future: asyncio.Future):
            self.exit_future = exit_future
            self.enough_data_future = enough_data_future
            self.output = bytearray()
            self.msg_counter = 0

        def pipe_data_received(self, fd, data):

            decoded = data.decode("utf8")
            print(decoded)
            if "msg" in decoded:
                self.msg_counter += 1

            self.output.extend(data)

            if self.msg_counter > 19:
                self.enough_data_future.set_result(self.msg_counter)

        def pipe_connection_lost(self, fd, exc):

            self.exit_future.set_result(self.output)

    @asyncio.coroutine
    def subprocess(loop):

        enough_data_ftr = asyncio.Future()
        exit_ftr = asyncio.Future()

        create = loop.subprocess_exec(
            lambda: TestProtocol(exit_ftr, enough_data_ftr),
            *args,
            stdout=asyncio.subprocess.PIPE, stdin=None, **kwargs
        )

        transport, protocol = yield from create

        yield from enough_data_ftr

        transport.close()

        return protocol.output

    loop = asyncio.get_event_loop()

    out = loop.run_until_complete(asyncio.async(subprocess(loop)))

    return out