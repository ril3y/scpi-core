"""Serial (USB/RS-232) transport for SCPI instruments.

Requires pyserial: pip install scpi-core[serial]
"""
from __future__ import annotations

try:
    import serial
except ImportError:
    serial = None

from .transport import Transport
from .errors import ScpiConnectionError, ScpiTimeoutError


class SerialTransport(Transport):
    """SCPI over serial port (USB-CDC, RS-232, virtual COM ports)."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 5.0,
        terminator: str = "\n",
    ):
        if serial is None:
            raise ImportError(
                "pyserial is required for SerialTransport. "
                "Install with: pip install pyscpi[serial]"
            )
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._terminator = terminator
        self._serial: "serial.Serial | None" = None

    @property
    def port(self) -> str:
        return self._port

    @property
    def baudrate(self) -> int:
        return self._baudrate

    @property
    def timeout(self) -> float:
        return self._timeout

    @timeout.setter
    def timeout(self, value: float):
        self._timeout = value
        if self._serial is not None:
            self._serial.timeout = value

    def connect(self):
        if self._serial is not None:
            return
        try:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                timeout=self._timeout,
            )
        except serial.SerialException as e:
            raise ScpiConnectionError(
                f"Cannot open serial port {self._port}: {e}"
            ) from e

    def disconnect(self):
        if self._serial is not None:
            try:
                self._serial.close()
            except serial.SerialException:
                pass
            self._serial = None

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def send(self, data: str) -> None:
        if self._serial is None:
            raise ScpiConnectionError("Not connected")
        payload = data if data.endswith(self._terminator) else data + self._terminator
        try:
            self._serial.write(payload.encode("ascii"))
        except serial.SerialException as e:
            raise ScpiConnectionError(f"Serial write failed: {e}") from e

    def send_raw(self, data: bytes) -> None:
        if self._serial is None:
            raise ScpiConnectionError("Not connected")
        try:
            self._serial.write(data)
        except serial.SerialException as e:
            raise ScpiConnectionError(f"Serial raw write failed: {e}") from e

    def receive(self, timeout: float | None = None) -> str:
        if self._serial is None:
            raise ScpiConnectionError("Not connected")
        prev_timeout = self._serial.timeout
        if timeout is not None:
            self._serial.timeout = timeout
        try:
            line = self._serial.readline()
            if not line:
                raise ScpiTimeoutError("No response from serial instrument")
            return line.decode("ascii", errors="replace").strip()
        except serial.SerialException as e:
            raise ScpiConnectionError(f"Serial read failed: {e}") from e
        finally:
            if timeout is not None and self._serial is not None:
                self._serial.timeout = prev_timeout

    def receive_raw(self, count: int, timeout: float | None = None) -> bytes:
        if self._serial is None:
            raise ScpiConnectionError("Not connected")
        prev_timeout = self._serial.timeout
        if timeout is not None:
            self._serial.timeout = timeout
        try:
            data = self._serial.read(count)
            if len(data) < count:
                raise ScpiTimeoutError(
                    f"Serial read: expected {count} bytes, got {len(data)}"
                )
            return bytes(data)
        except serial.SerialException as e:
            raise ScpiConnectionError(f"Serial raw read failed: {e}") from e
        finally:
            if timeout is not None and self._serial is not None:
                self._serial.timeout = prev_timeout

    def flush_input(self) -> None:
        """Discard any unread data in the receive buffer."""
        if self._serial is not None:
            self._serial.reset_input_buffer()
