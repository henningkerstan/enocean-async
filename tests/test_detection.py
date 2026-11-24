"""Tests for the detection of the serial protocol of an EnOcean module."""

import asyncio

import pytest

from enocean_async import SerialProtocol, detect_serial_protocol
from enocean_async.protocol.esp2.packet import (
    ESP2HeaderSequence,
    ESP2MessageCode,
    ESP2Packet,
)
from enocean_async.protocol.esp3.packet import ESP3Packet, ESP3PacketType
from enocean_async.protocol.esp3.response import ResponseCode

BASE_ID = bytes.fromhex("ff801280")

ANSWERS = {
    SerialProtocol.ESP3: ESP3Packet(
        ESP3PacketType.RESPONSE, bytes([ResponseCode.OK]) + BASE_ID, b"\x0a"
    ).to_bytes(),
    SerialProtocol.ESP2: ESP2Packet(
        ESP2HeaderSequence.RCT, ESP2MessageCode.INF_IDBASE, BASE_ID, bytes(4), 0x00
    ).to_bytes(),
}
REQUEST_STARTS = {SerialProtocol.ESP3: b"\x55", SerialProtocol.ESP2: b"\xa5\x5a"}


class FakeSerialPort:
    """Stands in for the serial transport, with a module of one serial protocol, or none, behind it."""

    def __init__(self, module: SerialProtocol | None) -> None:
        self.module = module
        self.protocol: asyncio.Protocol | None = None
        self.opened = 0
        self.baudrates: list[int] = []
        self.written: list[bytes] = []
        self.closed = False
        self.port_released = asyncio.Event()
        self.port_released.set()
        self.waiting_for_release = asyncio.Event()
        self.may_open = asyncio.Event()
        self.may_open.set()
        self.open_error: Exception | None = None

    def write(self, data: bytes) -> None:
        self.written.append(data)
        # a module only understands its own serial protocol at its own baudrate
        if (
            self.module is not None
            and self.baudrates[-1] == self.module.default_baudrate
            and data.startswith(REQUEST_STARTS[self.module])
        ):
            asyncio.get_running_loop().call_soon(
                self.protocol.data_received, ANSWERS[self.module]
            )

    async def reconfigure_port(self, *, baudrate: int) -> None:
        self.baudrates.append(baudrate)

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        self.waiting_for_release.set()
        await self.port_released.wait()


@pytest.fixture
def connect(monkeypatch: pytest.MonkeyPatch):
    """Put a fake serial port with the given module behind every opened port."""
    monkeypatch.setattr("enocean_async.protocol.detection._ANSWER_TIMEOUT", 0.05)

    def _connect(module: SerialProtocol | None) -> FakeSerialPort:
        port = FakeSerialPort(module)

        async def create_serial_connection(loop, protocol_factory, url, baudrate):
            await port.may_open.wait()
            if port.open_error is not None:
                raise port.open_error
            port.opened += 1
            port.baudrates.append(baudrate)
            port.protocol = protocol_factory()
            return port, port.protocol

        monkeypatch.setattr(
            "enocean_async.protocol.detection.serialx.create_serial_connection",
            create_serial_connection,
        )
        return port

    return _connect


@pytest.mark.parametrize(
    ("module", "expected_baudrates", "expected_requests"),
    [
        pytest.param(SerialProtocol.ESP3, [57600], 1, id="esp3_module"),
        pytest.param(SerialProtocol.ESP2, [57600, 9600], 2, id="esp2_module"),
        pytest.param(None, [57600, 9600], 2, id="no_module"),
    ],
)
async def test_detect_serial_protocol(
    connect,
    module: SerialProtocol | None,
    expected_baudrates: list[int],
    expected_requests: int,
):
    port = connect(module)

    assert await detect_serial_protocol("/dev/null") is module

    assert port.opened == 1
    assert port.baudrates == expected_baudrates
    assert len(port.written) == expected_requests
    assert port.closed


async def test_port_that_cannot_be_opened_has_no_module(
    monkeypatch: pytest.MonkeyPatch,
):
    async def create_serial_connection(loop, protocol_factory, url, baudrate):
        raise OSError("no such port")

    monkeypatch.setattr(
        "enocean_async.protocol.detection.serialx.create_serial_connection",
        create_serial_connection,
    )

    assert await detect_serial_protocol("/dev/null") is None


async def test_detection_waits_until_the_port_of_a_found_module_is_released(connect):
    port = connect(SerialProtocol.ESP2)
    port.port_released.clear()

    detection = asyncio.ensure_future(detect_serial_protocol("/dev/null"))
    await port.waiting_for_release.wait()

    assert port.closed
    assert not detection.done()

    port.port_released.set()
    assert await detection is SerialProtocol.ESP2


async def test_detection_does_not_wait_for_a_port_without_module(connect):
    port = connect(None)
    port.port_released.clear()

    assert await detect_serial_protocol("/dev/null") is None

    assert port.closed
    assert not port.waiting_for_release.is_set()


async def test_answer_in_the_other_serial_protocol_is_not_taken_for_a_module(connect):
    port = connect(SerialProtocol.ESP2)
    # an ESP2 module set to the ESP3 baudrate still does not speak ESP3
    port.module = None
    original_write = port.write

    def write(data: bytes) -> None:
        original_write(data)
        if port.baudrates[-1] == 57600:
            asyncio.get_running_loop().call_soon(
                port.protocol.data_received, ANSWERS[SerialProtocol.ESP2]
            )

    port.write = write

    assert await detect_serial_protocol("/dev/null") is None


async def let_the_late_open_end() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_port_that_does_not_open_in_time_has_no_module_and_is_closed_once_open(
    connect, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("enocean_async.protocol.detection._OPEN_TIMEOUT", 0.01)
    port = connect(SerialProtocol.ESP2)
    port.may_open.clear()

    assert await detect_serial_protocol("/dev/null") is None

    # nothing was sent, and the port is not left open when the open ends at last
    assert port.opened == 0
    # meanwhile the port is not opened a second time
    assert await detect_serial_protocol("/dev/null") is None
    port.may_open.set()
    await let_the_late_open_end()
    assert port.opened == 1
    assert port.closed
    assert not port.written


async def test_port_that_fails_to_open_after_the_detection_gave_up(
    connect, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("enocean_async.protocol.detection._OPEN_TIMEOUT", 0.01)
    port = connect(SerialProtocol.ESP2)
    port.may_open.clear()
    port.open_error = OSError("port is gone")

    assert await detect_serial_protocol("/dev/null") is None

    port.may_open.set()
    await let_the_late_open_end()
    assert port.opened == 0
    assert not port.closed


async def test_cancelled_detection_closes_the_port_once_it_is_open(connect):
    port = connect(SerialProtocol.ESP2)
    port.may_open.clear()

    detection = asyncio.ensure_future(detect_serial_protocol("/dev/null"))
    await asyncio.sleep(0)
    detection.cancel()
    with pytest.raises(asyncio.CancelledError):
        await detection

    port.may_open.set()
    await let_the_late_open_end()
    assert port.closed
    assert not port.written


async def test_port_is_detected_again_after_its_late_open_has_ended(
    connect, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("enocean_async.protocol.detection._OPEN_TIMEOUT", 0.01)
    port = connect(SerialProtocol.ESP2)
    port.may_open.clear()
    assert await detect_serial_protocol("/dev/null") is None
    port.may_open.set()
    await let_the_late_open_end()

    assert await detect_serial_protocol("/dev/null") is SerialProtocol.ESP2

    assert port.opened == 2
