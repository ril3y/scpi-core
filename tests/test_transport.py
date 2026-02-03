import socket
import threading
import time
import pytest

from scpi_core import TcpTransport, ScpiConnectionError, ScpiTimeoutError


def make_server(handler):
    """Create a TCP server on localhost, return (server_socket, port)."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    t = threading.Thread(target=handler, args=(srv,), daemon=True)
    t.start()
    return srv, port, t


class TestTcpConnect:
    def test_connect_disconnect(self):
        def handler(srv):
            conn, _ = srv.accept()
            conn.close()
            srv.close()

        srv, port, _ = make_server(handler)
        tp = TcpTransport("127.0.0.1", port, timeout=2.0)
        assert not tp.is_connected()
        tp.connect()
        assert tp.is_connected()
        tp.disconnect()
        assert not tp.is_connected()

    def test_connect_refused(self):
        tp = TcpTransport("127.0.0.1", 1, timeout=1.0)
        with pytest.raises(ScpiConnectionError):
            tp.connect()

    def test_double_connect_is_noop(self):
        def handler(srv):
            conn, _ = srv.accept()
            time.sleep(0.5)
            conn.close()
            srv.close()

        srv, port, _ = make_server(handler)
        tp = TcpTransport("127.0.0.1", port, timeout=2.0)
        tp.connect()
        tp.connect()  # should not raise
        tp.disconnect()

    def test_double_disconnect_is_noop(self):
        tp = TcpTransport("127.0.0.1", 1, timeout=1.0)
        tp.disconnect()
        tp.disconnect()  # should not raise


class TestTcpSendReceive:
    def test_send_and_receive(self):
        def handler(srv):
            conn, _ = srv.accept()
            data = b""
            while b"\n" not in data:
                data += conn.recv(1024)
            conn.sendall(b"REPLY\n")
            conn.close()
            srv.close()

        srv, port, _ = make_server(handler)
        tp = TcpTransport("127.0.0.1", port, timeout=2.0)
        tp.connect()
        tp.send("HELLO")
        resp = tp.receive()
        assert resp == "REPLY"
        tp.disconnect()

    def test_send_appends_newline(self):
        received = []

        def handler(srv):
            conn, _ = srv.accept()
            data = conn.recv(1024)
            received.append(data)
            conn.sendall(b"OK\n")
            conn.close()
            srv.close()

        srv, port, _ = make_server(handler)
        tp = TcpTransport("127.0.0.1", port, timeout=2.0)
        tp.connect()
        tp.send("TEST")
        tp.receive()
        tp.disconnect()
        assert received[0] == b"TEST\n"

    def test_send_does_not_double_newline(self):
        received = []

        def handler(srv):
            conn, _ = srv.accept()
            data = conn.recv(1024)
            received.append(data)
            conn.sendall(b"OK\n")
            conn.close()
            srv.close()

        srv, port, _ = make_server(handler)
        tp = TcpTransport("127.0.0.1", port, timeout=2.0)
        tp.connect()
        tp.send("TEST\n")
        tp.receive()
        tp.disconnect()
        assert received[0] == b"TEST\n"

    def test_receive_timeout(self):
        def handler(srv):
            conn, _ = srv.accept()
            time.sleep(5)  # never respond
            conn.close()
            srv.close()

        srv, port, _ = make_server(handler)
        tp = TcpTransport("127.0.0.1", port, timeout=2.0)
        tp.connect()
        tp.send("HELLO")
        with pytest.raises(ScpiTimeoutError):
            tp.receive(timeout=0.5)
        tp.disconnect()
        srv.close()

    def test_send_when_disconnected_raises(self):
        tp = TcpTransport("127.0.0.1", 1, timeout=1.0)
        with pytest.raises(ScpiConnectionError):
            tp.send("HELLO")

    def test_receive_when_disconnected_raises(self):
        tp = TcpTransport("127.0.0.1", 1, timeout=1.0)
        with pytest.raises(ScpiConnectionError):
            tp.receive()

    def test_connection_closed_by_server(self):
        def handler(srv):
            conn, _ = srv.accept()
            conn.close()
            srv.close()

        srv, port, _ = make_server(handler)
        tp = TcpTransport("127.0.0.1", port, timeout=2.0)
        tp.connect()
        tp.send("HELLO")
        with pytest.raises(ScpiConnectionError):
            tp.receive()
        tp.disconnect()


class TestTcpRawIO:
    def test_send_receive_raw(self):
        def handler(srv):
            conn, _ = srv.accept()
            data = b""
            while b"\n" not in data:
                data += conn.recv(1024)
            conn.sendall(b"\x00\x01\x02\x03\x04")
            conn.close()
            srv.close()

        srv, port, _ = make_server(handler)
        tp = TcpTransport("127.0.0.1", port, timeout=2.0)
        tp.connect()
        tp.send("WAV:DATA?")
        raw = tp.receive_raw(5)
        assert raw == b"\x00\x01\x02\x03\x04"
        tp.disconnect()


class TestTcpProperties:
    def test_host_port_timeout(self):
        tp = TcpTransport("192.168.1.100", 1234, timeout=3.0)
        assert tp.host == "192.168.1.100"
        assert tp.port == 1234
        assert tp.timeout == 3.0

    def test_timeout_setter(self):
        tp = TcpTransport("127.0.0.1", 1, timeout=1.0)
        tp.timeout = 5.0
        assert tp.timeout == 5.0
