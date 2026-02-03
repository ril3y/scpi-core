from __future__ import annotations

import socket
from abc import ABC, abstractmethod

from .errors import ScpiConnectionError, ScpiTimeoutError


class Transport(ABC):
    """Abstract base for SCPI transports (TCP, serial, USB-TMC, etc.)."""

    @abstractmethod
    def connect(self):
        """Open the connection."""

    @abstractmethod
    def disconnect(self):
        """Close the connection."""

    @abstractmethod
    def send(self, data: str) -> None:
        """Send a string to the instrument."""

    @abstractmethod
    def receive(self, timeout: float | None = None) -> str:
        """Read a response string from the instrument."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the transport is currently connected."""

    def send_raw(self, data: bytes) -> None:
        """Send raw bytes. Default implementation encodes via send()."""
        self.send(data.decode("ascii"))

    def receive_raw(self, count: int, timeout: float | None = None) -> bytes:
        """Read raw bytes. Subclasses should override for binary data."""
        raise NotImplementedError("This transport does not support raw byte reads")


class TcpTransport(Transport):
    """SCPI over TCP sockets (LAN/LXI instruments)."""

    def __init__(self, host: str, port: int = 5555, timeout: float = 5.0):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._socket: socket.socket | None = None

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def timeout(self) -> float:
        return self._timeout

    @timeout.setter
    def timeout(self, value: float):
        self._timeout = value
        if self._socket is not None:
            self._socket.settimeout(value)

    def connect(self):
        if self._socket is not None:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect((self._host, self._port))
            self._socket = sock
        except socket.timeout as e:
            raise ScpiConnectionError(
                f"Timeout connecting to {self._host}:{self._port}"
            ) from e
        except OSError as e:
            raise ScpiConnectionError(
                f"Cannot connect to {self._host}:{self._port}: {e}"
            ) from e

    def disconnect(self):
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def is_connected(self) -> bool:
        return self._socket is not None

    def send(self, data: str) -> None:
        if self._socket is None:
            raise ScpiConnectionError("Not connected")
        payload = data if data.endswith("\n") else data + "\n"
        try:
            self._socket.sendall(payload.encode("ascii"))
        except socket.timeout as e:
            raise ScpiTimeoutError(f"Timeout sending: {data!r}") from e
        except OSError as e:
            self._socket = None
            raise ScpiConnectionError(f"Send failed: {e}") from e

    def send_raw(self, data: bytes) -> None:
        if self._socket is None:
            raise ScpiConnectionError("Not connected")
        try:
            self._socket.sendall(data)
        except socket.timeout as e:
            raise ScpiTimeoutError("Timeout sending raw data") from e
        except OSError as e:
            self._socket = None
            raise ScpiConnectionError(f"Raw send failed: {e}") from e

    def receive(self, timeout: float | None = None) -> str:
        if self._socket is None:
            raise ScpiConnectionError("Not connected")
        prev_timeout = self._socket.gettimeout()
        if timeout is not None:
            self._socket.settimeout(timeout)
        try:
            return self._read_until_newline().strip()
        except socket.timeout as e:
            raise ScpiTimeoutError("Timeout waiting for response") from e
        except OSError as e:
            self._socket = None
            raise ScpiConnectionError(f"Receive failed: {e}") from e
        finally:
            if timeout is not None and self._socket is not None:
                self._socket.settimeout(prev_timeout)

    def receive_raw(self, count: int, timeout: float | None = None) -> bytes:
        if self._socket is None:
            raise ScpiConnectionError("Not connected")
        prev_timeout = self._socket.gettimeout()
        if timeout is not None:
            self._socket.settimeout(timeout)
        try:
            return self._read_bytes(count)
        except socket.timeout as e:
            raise ScpiTimeoutError(
                f"Timeout reading {count} raw bytes"
            ) from e
        except OSError as e:
            self._socket = None
            raise ScpiConnectionError(f"Raw receive failed: {e}") from e
        finally:
            if timeout is not None and self._socket is not None:
                self._socket.settimeout(prev_timeout)

    def _read_until_newline(self) -> str:
        buf = bytearray()
        while True:
            chunk = self._socket.recv(4096)
            if not chunk:
                raise ScpiConnectionError("Connection closed by instrument")
            buf.extend(chunk)
            if b"\n" in buf:
                break
        return buf.decode("ascii", errors="replace")

    def _read_bytes(self, count: int) -> bytes:
        buf = bytearray()
        while len(buf) < count:
            chunk = self._socket.recv(min(count - len(buf), 65536))
            if not chunk:
                raise ScpiConnectionError("Connection closed by instrument")
            buf.extend(chunk)
        return bytes(buf)
