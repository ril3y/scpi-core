class ScpiError(Exception):
    """Base exception for all SCPI errors."""


class ScpiConnectionError(ScpiError):
    """Raised when a connection cannot be established or is lost."""


class ScpiTimeoutError(ScpiError):
    """Raised when a command or query times out."""


class ScpiProtocolError(ScpiError):
    """Raised when the device returns an unexpected or malformed response."""
