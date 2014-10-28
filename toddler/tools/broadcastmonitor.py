__author__ = 'michal'
import asyncio
try:
    from socket import socketpair
except ImportError:
    from asyncio.windows_utils import socketpair

import socket
import collections

@asyncio.tasks.coroutine
def create_broadcast_datagram_endpoint(self, protocol_factory,
                                       local_addr=None, remote_addr=None, *,
                                       family=0, proto=0, flags=0):
    """Create datagram connection."""
    if not (local_addr or remote_addr):
        if family == 0:
            raise ValueError('unexpected address family')
        addr_pairs_info = (((family, proto), (None, None)),)
    else:
        # join addresss by (family, protocol)
        addr_infos = collections.OrderedDict()
        for idx, addr in ((0, local_addr), (1, remote_addr)):
            if addr is not None:
                assert isinstance(addr, tuple) and len(addr) == 2, (
                    '2-tuple is expected')

                try:
                    infos = yield from self.getaddrinfo(
                        *addr, family=family, type=socket.SOCK_DGRAM,
                        proto=proto, flags=flags)
                except TypeError:
                    if addr[0] == socket.INADDR_BROADCAST:
                        infos = [(socket.AF_INET, socket.SOCK_DGRAM,
                                  socket.SOL_UDP, '', ("", addr[1]))]
                if not infos:
                    raise OSError('getaddrinfo() returned empty list')

                for fam, _, pro, _, address in infos:
                    key = (fam, pro)
                    if key not in addr_infos:
                        addr_infos[key] = [None, None]
                    addr_infos[key][idx] = address

        # each addr has to have info for each (family, proto) pair
        addr_pairs_info = [
            (key, addr_pair) for key, addr_pair in addr_infos.items()
            if not ((local_addr and addr_pair[0] is None) or
                    (remote_addr and addr_pair[1] is None))]

        if not addr_pairs_info:
            raise ValueError('can not get address information')

    exceptions = []

    for ((family, proto),
         (local_address, remote_address)) in addr_pairs_info:
        sock = None
        r_addr = None
        try:
            sock = socket.socket(
                family=family, type=socket.SOCK_DGRAM, proto=proto)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)

            if local_addr:
                sock.bind(local_address)
            if remote_addr:
                yield from self.sock_connect(sock, remote_address)
                r_addr = remote_address
        except OSError as exc:
            if sock is not None:
                sock.close()
            exceptions.append(exc)
        else:
            break
    else:
        raise exceptions[0]

    protocol = protocol_factory()
    transport = self._make_datagram_transport(sock, protocol, r_addr)
    return transport, protocol

class BroadcastMonitor:


    def connection_made(self, transport: asyncio.Transport):

        self.transport = transport

        print("> connection made")
        # self.transport.write(b"test")

    def data_received(self, data):

        print("got:", data)

    def datagram_received(self, data, addr):

        print("git d:", addr, data)

    def eof_received(self):

        print("> Eof received")
        pass


if __name__ == "__main__":


    wsock = socket.socket(type=socket.SOCK_DGRAM)
    wsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    loop = asyncio.get_event_loop()


    try:
        connect = create_broadcast_datagram_endpoint(
            loop,
            BroadcastMonitor,
            local_addr=(socket.INADDR_BROADCAST, 8090))

        transport, protocol = loop.run_until_complete(connect)
        print("I'm alone")
    except OSError:
        print("I'm not alone")
        connect = create_broadcast_datagram_endpoint(
            loop,
            BroadcastMonitor,
            remote_addr=(socket.INADDR_BROADCAST, 8090))

        transport, protocol = loop.run_until_complete(connect)
        transport.sendto(b"HELLO", ("", 8090))

    try:
        loop.run_forever()
    except Exception as e:
        pass
    finally:
        transport.close()
        loop.close()