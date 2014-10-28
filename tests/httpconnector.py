__author__ = 'michal'

import unittest
from toddler.crawler.connector.http import HttpConnector
import asyncio

class BroadcastMonitor(asyncio.Protocol):


    def __init__(self, cb_data_received):

        self.cb_data_received = cb_data_received

    def connection_made(self, transport: asyncio.Transport):

        self.transport = transport

    def data_received(self, data):

        self.cb_data_received(data)


    def eof_received(self):

        print("> Eof received")
        pass


class HttpConnectorTest(unittest.TestCase):


    def testBroadcast(self):

        httpconnector = HttpConnector({"broadcastPort": 8090})
        loop = httpconnector.loop

        # connect = loop.create_datagram_endpoint(
        #     lambda: BroadcastMonitor(message_handling),
        #     remote_addr=('255.255.255.255', 8090))

        httpconnector.setup_broadcast_listener()

        loop.run_forever()
        loop.close()

