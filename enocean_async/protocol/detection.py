"""Detection of the serial protocol an EnOcean module speaks."""

import asyncio
import logging

import serialx

from .esp2.protocol import EnOceanSerialProtocol2
from .esp3.common_command import CommonCommandTelegram
from .esp3.packet import ESP3Packet, ESP3PacketType
from .esp3.protocol import EnOceanSerialProtocol3
from .esp3.response import ResponseCode, ResponseTelegram
from .serial_protocol import SerialProtocol

_LOGGER = logging.getLogger(__name__)

_ANSWER_TIMEOUT = 0.5
"""Seconds to wait for the module's answer in each serial protocol."""

_OPEN_TIMEOUT = 2.0
"""Seconds to wait for the serial port to open. A port opens at once, unless the operating system is still closing it: after output that never reached a module, that can take about 30 seconds."""

_PORT_RELEASE_TIMEOUT = 1.0
"""Seconds to wait for the serial port to be released after a module was found, so that the port can be opened again right away."""

_PROTOCOLS = (SerialProtocol.ESP3, SerialProtocol.ESP2)
"""The serial protocols in the order they are tried."""

_ports_in_use: dict[str, asyncio.Task] = {}
"""Map from port name to the task opening that port, for the ports whose open a detection no longer waits for. While a port is here, it is not opened again."""


def _close_when_opened(port: str, open_task: asyncio.Task) -> None:
    """Close a port that opened after the detection stopped waiting for it.

    An open the operating system holds cannot be cancelled, so the port is closed as soon as it is open.
    """

    def close(task: asyncio.Task) -> None:
        del _ports_in_use[port]
        if task.cancelled() or task.exception() is not None:
            return
        transport, _ = task.result()
        transport.close()

    _ports_in_use[port] = open_task
    open_task.add_done_callback(close)


class _Probe(asyncio.Protocol):
    """Hands received bytes to the parser of the serial protocol being tried and notes whether the module answered.

    Towards the parsers it stands in for the gateway.
    """

    def __init__(self) -> None:
        self.parser: EnOceanSerialProtocol2 | EnOceanSerialProtocol3 | None = None
        self.ok_received = asyncio.Event()

    def data_received(self, data: bytes) -> None:
        if self.parser is not None:
            self.parser.data_received(data)

    def process_esp3_packet(self, packet: ESP3Packet) -> None:
        """Called by the parser for every valid packet from the module."""
        if packet.packet_type != ESP3PacketType.RESPONSE:
            return
        try:
            response = ResponseTelegram.from_esp3_packet(packet)
        except ValueError:
            return
        if response.return_code == ResponseCode.OK:
            self.ok_received.set()


def _parser_for(
    protocol: SerialProtocol, probe: _Probe
) -> EnOceanSerialProtocol2 | EnOceanSerialProtocol3:
    if protocol is SerialProtocol.ESP2:
        return EnOceanSerialProtocol2(probe)  # type: ignore[arg-type]
    return EnOceanSerialProtocol3(probe)  # type: ignore[arg-type]


async def detect_serial_protocol(port: str) -> SerialProtocol | None:
    """Return the serial protocol the EnOcean module on the port speaks, or ``None`` if no module answers.

    The port is opened once. Each serial protocol is tried at its own baudrate by asking the module for its base ID; ESP3 first, then ESP2. A port that cannot be opened, does not open within two seconds, or fails while the module is being asked, counts as "no module".

    Opening the port once matters: on a port whose output never reaches a module, the operating system can hold a close for about 30 seconds, and a second open waits behind it. The same happens to a detection that follows another one on such a port; it gives up after two seconds, and the port is closed again as soon as it has opened. Until then, further detections on that port report no module at once.
    """
    if port in _ports_in_use:
        _LOGGER.debug(f"{port} is still being opened by an earlier detection.")
        return None

    loop = asyncio.get_running_loop()
    probe = _Probe()
    baudrate = _PROTOCOLS[0].default_baudrate

    open_task = loop.create_task(
        serialx.create_serial_connection(loop, lambda: probe, port, baudrate=baudrate)
    )
    try:
        done, _ = await asyncio.wait({open_task}, timeout=_OPEN_TIMEOUT)
    except asyncio.CancelledError:
        _close_when_opened(port, open_task)
        raise
    if not done:
        _LOGGER.debug(f"{port} did not open within {_OPEN_TIMEOUT} s.")
        _close_when_opened(port, open_task)
        return None
    try:
        transport, _ = open_task.result()
    except Exception as e:
        _LOGGER.debug(f"Cannot open {port} to detect the serial protocol: {e}")
        return None

    detected: SerialProtocol | None = None
    try:
        for protocol in _PROTOCOLS:
            if protocol.default_baudrate != baudrate:
                baudrate = protocol.default_baudrate
                await transport.reconfigure_port(baudrate=baudrate)

            probe.parser = _parser_for(protocol, probe)
            transport.write(
                probe.parser.serialize(
                    CommonCommandTelegram.CO_RD_IDBASE().to_esp3_packet()
                )
            )
            try:
                async with asyncio.timeout(_ANSWER_TIMEOUT):
                    await probe.ok_received.wait()
            except TimeoutError:
                _LOGGER.debug(f"No {protocol} module answered on {port}.")
                continue

            detected = protocol
            break
    except OSError as e:
        # e.g. the module was unplugged during the detection
        _LOGGER.debug(f"Serial port {port} failed during the detection: {e}")
    finally:
        transport.close()

    if detected is not None:
        try:
            async with asyncio.timeout(_PORT_RELEASE_TIMEOUT):
                # shielded, so that giving up does not cancel the transport's own close
                await asyncio.shield(transport.wait_closed())
        except TimeoutError:
            _LOGGER.debug(
                f"Serial port {port} was not released within {_PORT_RELEASE_TIMEOUT} s."
            )

    return detected
