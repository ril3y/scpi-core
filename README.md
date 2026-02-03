<p align="center">
  <img src="https://raw.githubusercontent.com/ril3y/scpi-core/main/scpi-core.png" alt="scpi-core logo" width="400">
</p>

# scpi-core

A device-agnostic SCPI (Standard Commands for Programmable Instruments) communication library for Python.

## Why scpi-core?

Most SCPI libraries fall into one of two traps: they're either tightly coupled to a specific vendor's instruments, or they drag in heavy dependencies like NI-VISA just to send ASCII strings over a socket.

scpi-core takes a different approach:

- **Device-agnostic** -- No vendor-specific code. No hardcoded instrument quirks. This is a transport and protocol layer only. Instrument-specific logic belongs in your driver library, not here.
- **Zero required dependencies** -- TCP transport works out of the box with the Python standard library. Serial transport is an optional extra (`pip install scpi-core[serial]`).
- **Proper timeout handling** -- Every send, receive, and connection operation has configurable timeouts. No infinite hangs when an instrument doesn't respond.
- **Clean error hierarchy** -- Catch `ScpiTimeoutError`, `ScpiConnectionError`, or `ScpiProtocolError` individually, or catch the base `ScpiError` for everything.
- **Transport abstraction** -- Swap between TCP, serial, or your own custom transport without changing instrument driver code.

## Installation

```bash
pip install scpi-core
```

With serial port support:

```bash
pip install scpi-core[serial]
```

## Quick Start

### TCP (LAN/LXI instruments)

```python
from scpi_core import TcpTransport, ScpiDevice

transport = TcpTransport("192.168.1.100", port=5555, timeout=5.0)

with ScpiDevice(transport) as dev:
    print(dev.idn())
    dev.command(":CHAN1:DISP ON")
    scale = dev.query_float(":CHAN1:SCAL?")
    print(f"Channel 1 scale: {scale} V/div")
```

### Serial (USB-CDC / COM port instruments)

```python
from scpi_core import SerialTransport, ScpiDevice

transport = SerialTransport("COM3", baudrate=115200, timeout=5.0)

with ScpiDevice(transport) as dev:
    print(dev.idn())
```

### Typed Queries

```python
# Parse response as float
voltage = dev.query_float(":MEAS:VAVG?")

# Parse response as int
depth = dev.query_int(":ACQ:MDEP?")

# Parse response as bool (handles 0/1 and ON/OFF)
enabled = dev.query_bool(":CHAN1:DISP?")
```

### IEEE 488.2 Common Commands

```python
dev.reset()           # *RST
dev.clear_status()    # *CLS
dev.wait()            # *WAI
dev.opc()             # *OPC? -- returns True when complete
dev.save_state(1)     # *SAV 1
dev.recall_state(1)   # *RCL 1
result = dev.self_test()  # *TST? -- 0 = pass
error = dev.check_error() # :SYST:ERR? -- None if no error
```

## Building Instrument Drivers on scpi-core

scpi-core is designed as a foundation layer. Instrument-specific libraries should depend on scpi-core for transport and use composition to build their API.

### Pattern: Subsystem Composition

```python
from scpi_core import TcpTransport, ScpiDevice

class ChannelSubsystem:
    """Controls oscilloscope channel settings."""

    def __init__(self, device: ScpiDevice):
        self._dev = device

    def set_scale(self, channel: str, scale: float):
        self._dev.command(f":{channel}:SCAL {scale}")

    def get_scale(self, channel: str) -> float:
        return self._dev.query_float(f":{channel}:SCAL?")

    def set_display(self, channel: str, enabled: bool):
        state = "ON" if enabled else "OFF"
        self._dev.command(f":{channel}:DISP {state}")


class MyOscilloscope:
    """Driver for a specific oscilloscope model."""

    def __init__(self, host: str, port: int = 5555):
        self._transport = TcpTransport(host, port)
        self._dev = ScpiDevice(self._transport)
        self.channel = ChannelSubsystem(self._dev)

    def __enter__(self):
        self._transport.connect()
        return self

    def __exit__(self, *args):
        self._transport.disconnect()
```

### Guidelines for Instrument Libraries

- **Do not** put vendor-specific code in scpi-core. Keep it in your instrument library.
- **Do** use `ScpiDevice` as the interface between your subsystems and the transport.
- **Do** use the typed query methods (`query_float`, `query_int`, `query_bool`) to keep parsing out of your driver code.
- **Do** use the transport abstraction so your driver works over TCP, serial, or any future transport without changes.
- **Do not** subclass `ScpiDevice`. Use composition -- your instrument class *has* a `ScpiDevice`, it is not one.

### Custom Transports

Implement the `Transport` abstract class to add new communication backends:

```python
from scpi_core.transport import Transport

class MyCustomTransport(Transport):
    def connect(self):
        ...

    def disconnect(self):
        ...

    def send(self, data: str) -> None:
        ...

    def receive(self, timeout: float | None = None) -> str:
        ...

    def is_connected(self) -> bool:
        ...
```

Then use it with `ScpiDevice` like any other transport:

```python
transport = MyCustomTransport(...)
dev = ScpiDevice(transport)
```

## API Reference

### Transports

| Class | Description | Install |
|---|---|---|
| `TcpTransport(host, port, timeout)` | SCPI over TCP/LAN | Built-in |
| `SerialTransport(port, baudrate, timeout)` | SCPI over serial/USB-CDC | `pip install scpi-core[serial]` |

### ScpiDevice Methods

| Method | Description |
|---|---|
| `command(cmd)` | Send a command (no response) |
| `query(cmd)` | Send a query, return string response |
| `query_float(cmd)` | Query and parse as float |
| `query_int(cmd)` | Query and parse as int |
| `query_bool(cmd)` | Query and parse as bool (0/1/ON/OFF) |
| `query_raw(cmd, count)` | Query and read raw bytes |
| `idn()` | `*IDN?` |
| `reset()` | `*RST` |
| `clear_status()` | `*CLS` |
| `opc()` | `*OPC?` |
| `wait()` | `*WAI` |
| `self_test()` | `*TST?` |
| `save_state(slot)` | `*SAV` |
| `recall_state(slot)` | `*RCL` |
| `check_error()` | `:SYST:ERR?` (returns None if no error) |

### Errors

| Exception | When |
|---|---|
| `ScpiError` | Base class for all errors |
| `ScpiConnectionError` | Connection failed or lost |
| `ScpiTimeoutError` | Operation timed out |
| `ScpiProtocolError` | Unexpected/malformed response |

## License

MIT
