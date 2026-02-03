import pytest
from scpi_core import ScpiDevice, ScpiProtocolError
from scpi_core.transport import Transport


class MockTransport(Transport):
    """In-memory transport for testing ScpiDevice without sockets."""

    def __init__(self):
        self._connected = False
        self._sent = []
        self._responses = {}
        self._response_queue = {}

    def connect(self):
        self._connected = True

    def disconnect(self):
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def send(self, data: str) -> None:
        self._sent.append(data)

    def receive(self, timeout: float | None = None) -> str:
        cmd = self._sent[-1] if self._sent else ""
        if cmd in self._response_queue and self._response_queue[cmd]:
            return self._response_queue[cmd].pop(0)
        if cmd in self._responses:
            return self._responses[cmd]
        return ""

    def set_response(self, query: str, response: str):
        self._responses[query] = response

    def queue_response(self, query: str, response: str):
        self._response_queue.setdefault(query, []).append(response)

    @property
    def sent(self):
        return self._sent

    def last_sent(self):
        return self._sent[-1] if self._sent else None


@pytest.fixture
def mock_transport():
    return MockTransport()


@pytest.fixture
def device(mock_transport):
    mock_transport.connect()
    return ScpiDevice(mock_transport, auto_connect=False)


class TestCommand:
    def test_command_sends(self, device, mock_transport):
        device.command(":CHAN1:DISP ON")
        assert mock_transport.last_sent() == ":CHAN1:DISP ON"

    def test_multiple_commands(self, device, mock_transport):
        device.command(":RUN")
        device.command(":STOP")
        assert mock_transport.sent == [":RUN", ":STOP"]


class TestQuery:
    def test_query_returns_response(self, device, mock_transport):
        mock_transport.set_response("*IDN?", "RIGOL,MSO5074")
        assert device.query("*IDN?") == "RIGOL,MSO5074"

    def test_query_float(self, device, mock_transport):
        mock_transport.set_response(":CHAN1:SCAL?", "1.5")
        assert device.query_float(":CHAN1:SCAL?") == 1.5

    def test_query_float_bad_response(self, device, mock_transport):
        mock_transport.set_response(":CHAN1:SCAL?", "GARBAGE")
        with pytest.raises(ScpiProtocolError):
            device.query_float(":CHAN1:SCAL?")

    def test_query_int(self, device, mock_transport):
        mock_transport.set_response(":ACQ:MDEP?", "10000")
        assert device.query_int(":ACQ:MDEP?") == 10000

    def test_query_int_bad_response(self, device, mock_transport):
        mock_transport.set_response(":ACQ:MDEP?", "NOPE")
        with pytest.raises(ScpiProtocolError):
            device.query_int(":ACQ:MDEP?")

    def test_query_bool_true(self, device, mock_transport):
        mock_transport.set_response(":CHAN1:DISP?", "1")
        assert device.query_bool(":CHAN1:DISP?") is True

    def test_query_bool_false(self, device, mock_transport):
        mock_transport.set_response(":CHAN1:DISP?", "0")
        assert device.query_bool(":CHAN1:DISP?") is False

    def test_query_bool_on_off(self, device, mock_transport):
        mock_transport.set_response(":DVM:ENAB?", "ON")
        assert device.query_bool(":DVM:ENAB?") is True

    def test_query_bool_bad_response(self, device, mock_transport):
        mock_transport.set_response(":CHAN1:DISP?", "MAYBE")
        with pytest.raises(ScpiProtocolError):
            device.query_bool(":CHAN1:DISP?")


class TestIEEE488:
    def test_idn(self, device, mock_transport):
        mock_transport.set_response("*IDN?", "RIGOL,MSO5074,SN123,1.0")
        assert device.idn() == "RIGOL,MSO5074,SN123,1.0"

    def test_reset(self, device, mock_transport):
        device.reset()
        assert mock_transport.last_sent() == "*RST"

    def test_clear_status(self, device, mock_transport):
        device.clear_status()
        assert mock_transport.last_sent() == "*CLS"

    def test_opc(self, device, mock_transport):
        mock_transport.set_response("*OPC?", "1")
        assert device.opc() is True

    def test_wait(self, device, mock_transport):
        device.wait()
        assert mock_transport.last_sent() == "*WAI"

    def test_save_recall_state(self, device, mock_transport):
        device.save_state(3)
        assert mock_transport.last_sent() == "*SAV 3"
        device.recall_state(3)
        assert mock_transport.last_sent() == "*RCL 3"

    def test_check_error_none(self, device, mock_transport):
        mock_transport.set_response(":SYST:ERR?", "0,No error")
        assert device.check_error() is None

    def test_check_error_present(self, device, mock_transport):
        mock_transport.set_response(":SYST:ERR?", "-100,Command error")
        assert device.check_error() == "-100,Command error"


class TestContextManager:
    def test_with_statement(self, mock_transport):
        with ScpiDevice(mock_transport, auto_connect=True) as dev:
            assert dev.is_connected()
        assert not dev.is_connected()

    def test_auto_connect_on_enter(self, mock_transport):
        dev = ScpiDevice(mock_transport, auto_connect=False)
        assert not dev.is_connected()
        with dev:
            assert dev.is_connected()
        assert not dev.is_connected()
