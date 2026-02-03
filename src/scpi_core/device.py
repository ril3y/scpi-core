from .transport import Transport
from .errors import ScpiProtocolError, ScpiTimeoutError


class ScpiDevice:
    """High-level SCPI instrument interface built on a Transport.

    Provides command(), query(), and common IEEE 488.2 operations.
    """

    def __init__(self, transport: Transport, auto_connect: bool = True):
        self._transport = transport
        if auto_connect and not transport.is_connected():
            transport.connect()

    @property
    def transport(self) -> Transport:
        return self._transport

    # -- Connection lifecycle --

    def connect(self):
        self._transport.connect()

    def disconnect(self):
        self._transport.disconnect()

    def is_connected(self) -> bool:
        return self._transport.is_connected()

    def __enter__(self):
        if not self._transport.is_connected():
            self._transport.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    # -- Core SCPI operations --

    def command(self, cmd: str) -> None:
        """Send a command (no response expected)."""
        self._transport.send(cmd)

    def query(self, cmd: str, timeout: float | None = None) -> str:
        """Send a query and return the response string."""
        self._transport.send(cmd)
        return self._transport.receive(timeout=timeout)

    def query_float(self, cmd: str, timeout: float | None = None) -> float:
        """Send a query and parse the response as a float."""
        resp = self.query(cmd, timeout=timeout)
        try:
            return float(resp)
        except ValueError:
            raise ScpiProtocolError(f"Expected float, got {resp!r} for {cmd!r}")

    def query_int(self, cmd: str, timeout: float | None = None) -> int:
        """Send a query and parse the response as an integer."""
        resp = self.query(cmd, timeout=timeout)
        try:
            return int(resp)
        except ValueError:
            raise ScpiProtocolError(f"Expected int, got {resp!r} for {cmd!r}")

    def query_bool(self, cmd: str, timeout: float | None = None) -> bool:
        """Send a query and parse 0/1 or OFF/ON response as bool."""
        resp = self.query(cmd, timeout=timeout).strip().upper()
        if resp in ("1", "ON"):
            return True
        if resp in ("0", "OFF"):
            return False
        raise ScpiProtocolError(f"Expected boolean, got {resp!r} for {cmd!r}")

    def query_raw(self, cmd: str, count: int, timeout: float | None = None) -> bytes:
        """Send a query and read a fixed number of raw bytes."""
        self._transport.send(cmd)
        return self._transport.receive_raw(count, timeout=timeout)

    # -- IEEE 488.2 common commands --

    def idn(self) -> str:
        """Query instrument identity (*IDN?)."""
        return self.query("*IDN?")

    def reset(self) -> None:
        """Reset instrument to factory defaults (*RST)."""
        self.command("*RST")

    def clear_status(self) -> None:
        """Clear status registers (*CLS)."""
        self.command("*CLS")

    def opc(self) -> bool:
        """Query operation complete (*OPC?)."""
        return self.query("*OPC?").strip() == "1"

    def wait(self) -> None:
        """Wait for pending operations to complete (*WAI)."""
        self.command("*WAI")

    def self_test(self) -> int:
        """Run self-test and return result (*TST?). 0 = pass."""
        return self.query_int("*TST?")

    def save_state(self, slot: int) -> None:
        """Save instrument state to internal memory (*SAV)."""
        self.command(f"*SAV {slot}")

    def recall_state(self, slot: int) -> None:
        """Recall instrument state from internal memory (*RCL)."""
        self.command(f"*RCL {slot}")

    def check_error(self) -> str | None:
        """Query system error queue. Returns None if no error."""
        resp = self.query(":SYST:ERR?")
        if resp.startswith("0,") or resp.startswith("+0,"):
            return None
        return resp
