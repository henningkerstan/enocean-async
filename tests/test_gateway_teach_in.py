"""Tests for 4BS teach-in at the Gateway (module simulated on the serial level)."""

import asyncio

import pytest

from enocean_async import EEP, EURID, BaseAddress, Gateway
from enocean_async.eep.manufacturer import Manufacturer
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram
from enocean_async.protocol.esp3.common_command import CommonCommandCode
from enocean_async.protocol.esp3.packet import ESP3Packet, ESP3PacketType
from enocean_async.protocol.esp3.protocol import EnOceanSerialProtocol3
from enocean_async.protocol.esp3.response import ResponseCode

BASE_ID = BaseAddress("FF:80:12:80")
MODULE_EURID = EURID("05:00:00:01")
SENSOR = EURID("01:23:45:67")


class FakeESP3Module:
    """Stands in for the serial transport and answers like an ESP3 module."""

    def __init__(self) -> None:
        self.protocol: EnOceanSerialProtocol3 | None = None
        self.sent_telegrams: list[ERP1Telegram] = []

    def write(self, data: bytes) -> None:
        data_length = (data[1] << 8) | data[2]
        optional_length = data[3]
        packet = ESP3Packet(
            ESP3PacketType(data[4]),
            data[6 : 6 + data_length],
            data[6 + data_length : 6 + data_length + optional_length],
        )

        answer = bytes([ResponseCode.OK])
        optional = b""
        if packet.packet_type == ESP3PacketType.RADIO_ERP1:
            self.sent_telegrams.append(ERP1Telegram.from_esp3(packet))
        elif packet.data[0] == CommonCommandCode.CO_RD_IDBASE:
            answer += bytes(BASE_ID.bytelist)
            optional = b"\x0a"
        elif packet.data[0] == CommonCommandCode.CO_RD_VERSION:
            answer += bytes([2, 11, 1, 0]) + bytes([2, 6, 3, 0])
            answer += bytes(MODULE_EURID.bytelist) + bytes(4)
            answer += b"GATEWAYCTRL".ljust(16, b"\x00")

        response = ESP3Packet(ESP3PacketType.RESPONSE, answer, optional)
        asyncio.get_running_loop().call_soon(
            self.protocol.data_received, response.to_bytes()
        )

    def close(self) -> None:
        pass

    def receive(self, telegram: ERP1Telegram) -> None:
        """Simulate a telegram received over the air."""
        self.protocol.data_received(telegram.to_esp3().to_bytes())


def teach_in_query(func: int, type_: int, manufacturer: Manufacturer) -> ERP1Telegram:
    """A 4BS teach-in telegram with EEP and manufacturer ID, as a sensor sends it."""
    telegram = ERP1Telegram(RORG.RORG_4BS, bytes(4), SENSOR)
    telegram.set_bitstring_raw_value(0, 6, func)
    telegram.set_bitstring_raw_value(6, 7, type_)
    telegram.set_bitstring_raw_value(13, 11, manufacturer.id)
    telegram.set_bitstring_raw_value(24, 1, 1)  # with EEP and manufacturer ID
    return telegram


@pytest.fixture
def module(monkeypatch: pytest.MonkeyPatch) -> FakeESP3Module:
    fake = FakeESP3Module()

    async def create_serial_connection(loop, protocol_factory, port, baudrate):
        fake.protocol = protocol_factory()
        fake.protocol.connection_made(fake)
        return fake, fake.protocol

    monkeypatch.setattr(
        "enocean_async.gateway.serialx.create_serial_connection",
        create_serial_connection,
    )
    return fake


@pytest.fixture
async def gateway(module: FakeESP3Module):
    gateway = Gateway("/dev/null")
    await gateway.start(auto_reconnect=False)
    await gateway.start_learning(timeout=5)
    yield gateway
    await gateway.stop()


@pytest.fixture
def taught_in(gateway: Gateway) -> list[tuple[EURID, EEP]]:
    taught: list[tuple[EURID, EEP]] = []
    gateway.add_device_taught_in_callback(
        lambda address, eep: taught.append((address, eep))
    )
    return taught


async def settle() -> None:
    """Let the gateway dispatch its callbacks and send its teach-in response."""
    await asyncio.sleep(0.05)


async def test_manufacturer_specific_eep_is_used_if_supported(module, taught_in):
    module.receive(teach_in_query(0x06, 0x01, Manufacturer.ELTAKO))
    await settle()

    assert taught_in == [(SENSOR, EEP("A5-06-01.ELTAKO"))]


@pytest.mark.parametrize(
    "manufacturer", [Manufacturer.THERMOKON, Manufacturer.ELTAKO, Manufacturer.RESERVED]
)
async def test_generic_eep_is_used_if_manufacturer_specific_eep_is_not_supported(
    module, taught_in, manufacturer
):
    module.receive(teach_in_query(0x04, 0x02, manufacturer))
    await settle()

    assert taught_in == [(SENSOR, EEP("A5-04-02"))]


async def test_teach_in_response_echoes_eep_and_manufacturer_of_the_query(
    module, taught_in
):
    module.receive(teach_in_query(0x04, 0x02, Manufacturer.THERMOKON))
    await settle()

    assert len(module.sent_telegrams) == 1
    response = module.sent_telegrams[0]
    assert response.bitstring_raw_value(0, 6) == 0x04
    assert response.bitstring_raw_value(6, 7) == 0x02
    assert response.bitstring_raw_value(13, 11) == Manufacturer.THERMOKON.id


async def test_repeated_teach_in_with_generic_fallback_registers_once(
    module, taught_in
):
    module.receive(teach_in_query(0x04, 0x02, Manufacturer.THERMOKON))
    await settle()
    module.receive(teach_in_query(0x04, 0x02, Manufacturer.THERMOKON))
    await settle()

    assert taught_in == [(SENSOR, EEP("A5-04-02"))]


async def test_unsupported_eep_is_ignored(module, taught_in):
    module.receive(teach_in_query(0x3F, 0x7F, Manufacturer.THERMOKON))
    await settle()

    assert taught_in == []
    assert module.sent_telegrams == []
