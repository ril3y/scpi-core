from .transport import Transport, TcpTransport
from .device import ScpiDevice
from .errors import ScpiError, ScpiConnectionError, ScpiTimeoutError, ScpiProtocolError

# Serial transport is optional (requires pyserial)
try:
    from .serial_transport import SerialTransport
except ImportError:
    SerialTransport = None

__all__ = [
    "Transport",
    "TcpTransport",
    "SerialTransport",
    "ScpiDevice",
    "ScpiError",
    "ScpiConnectionError",
    "ScpiTimeoutError",
    "ScpiProtocolError",
]
