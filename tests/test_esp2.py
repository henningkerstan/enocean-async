"""Tests for the ESP2 packet structure, its ESP3 translation and the ESP2 serial protocol."""

import pytest

from enocean_async.address import EURID
from enocean_async.protocol.erp1.rorg import RORG
from enocean_async.protocol.erp1.telegram import ERP1Telegram
from enocean_async.protocol.esp2.packet import (
    ESP2ORG,
    ESP2HeaderSequence,
    ESP2Packet,
    checksum,
)
from enocean_async.protocol.esp2.protocol import EnOceanSerialProtocol2
from enocean_async.protocol.esp3.packet import ESP3Packet, ESP3PacketType

SENDER = bytes.fromhex("01234567")

# A rocker press as an ESP2 module delivers it: RPS, DATA_BYTE3 = 0x70, status 0x30.
RPS_PRESS = bytes.fromhex("a55a0b05700000000123456730" + "80")
RPS_RELEASE = bytes.fromhex("a55a0b05000000000123456720" + "00")


def make_packet(org: int, data: bytes, status: int = 0x00) -> ESP2Packet:
    return ESP2Packet(ESP2HeaderSequence.RRT, org, data, SENDER, status)


class FakeGateway:
    """Collects what the serial protocol hands to the gateway."""

    def __init__(self) -> None:
        self.packets: list[ESP3Packet] = []
        self.connected = False
        self.lost: list[Exception | None] = []

    def connection_made(self) -> None:
        self.connected = True

    def connection_lost(self, exception: Exception | None) -> None:
        self.lost.append(exception)

    def process_esp3_packet(self, packet: ESP3Packet) -> None:
        self.packets.append(packet)


@pytest.fixture
def gateway() -> FakeGateway:
    return FakeGateway()


@pytest.fixture
def protocol(gateway: FakeGateway) -> EnOceanSerialProtocol2:
    return EnOceanSerialProtocol2(gateway)


# ---------------------------------------------------------------------------
# ESP2Packet
# ---------------------------------------------------------------------------


def test_checksum_is_low_byte_of_sum():
    assert checksum(bytes([0x01, 0x02, 0x03])) == 0x06
    assert checksum(bytes([0xFF, 0xFF, 0x03])) == 0x01


def test_from_bytes_parses_known_packet():
    packet = ESP2Packet.from_bytes(RPS_PRESS)

    assert packet.header_sequence == ESP2HeaderSequence.RRT
    assert packet.org == ESP2ORG.ORG_RPS
    assert packet.data == bytes.fromhex("70000000")
    assert packet.sender == SENDER
    assert packet.status == 0x30


def test_to_bytes_round_trip():
    assert ESP2Packet.from_bytes(RPS_PRESS).to_bytes() == RPS_PRESS
    assert ESP2Packet.from_bytes(RPS_RELEASE).to_bytes() == RPS_RELEASE


def test_from_bytes_rejects_wrong_length():
    with pytest.raises(ValueError):
        ESP2Packet.from_bytes(RPS_PRESS[:-1])


def test_from_bytes_rejects_missing_sync():
    with pytest.raises(ValueError):
        ESP2Packet.from_bytes(b"\x00" + RPS_PRESS[1:])


def test_from_bytes_rejects_bad_checksum():
    corrupted = RPS_PRESS[:-1] + bytes([RPS_PRESS[-1] ^ 0x01])
    with pytest.raises(ValueError):
        ESP2Packet.from_bytes(corrupted)


def test_from_bytes_rejects_unexpected_length_field():
    body = bytes([0x0A]) + RPS_PRESS[3:13]
    with pytest.raises(ValueError):
        ESP2Packet.from_bytes(RPS_PRESS[:2] + body + bytes([checksum(body)]))


def test_constructor_rejects_wrong_field_sizes():
    with pytest.raises(ValueError):
        ESP2Packet(ESP2HeaderSequence.RRT, ESP2ORG.ORG_RPS, b"\x70", SENDER)
    with pytest.raises(ValueError):
        ESP2Packet(ESP2HeaderSequence.RRT, ESP2ORG.ORG_RPS, bytes(4), SENDER[:3])


# ---------------------------------------------------------------------------
# ESP2 -> ESP3
# ---------------------------------------------------------------------------


def test_rps_translates_to_erp1():
    erp1 = ERP1Telegram.from_esp3(ESP2Packet.from_bytes(RPS_PRESS).to_esp3())

    assert erp1.rorg == RORG.RORG_RPS
    assert erp1.telegram_data == b"\x70"
    assert erp1.sender == EURID("01:23:45:67")
    assert erp1.status == 0x30
    assert erp1.rssi is None
    assert erp1.destination is None


def test_1bs_translates_to_erp1():
    packet = make_packet(ESP2ORG.ORG_1BS, bytes.fromhex("09000000"))
    erp1 = ERP1Telegram.from_esp3(packet.to_esp3())

    assert erp1.rorg == RORG.RORG_1BS
    assert erp1.telegram_data == b"\x09"


def test_4bs_translates_to_erp1():
    packet = make_packet(ESP2ORG.ORG_4BS, bytes.fromhex("02640009"))
    erp1 = ERP1Telegram.from_esp3(packet.to_esp3())

    assert erp1.rorg == RORG.RORG_4BS
    assert erp1.telegram_data == bytes.fromhex("02640009")


def test_unsupported_org_is_not_translated():
    with pytest.raises(ValueError):
        make_packet(0x0A, bytes(4)).to_esp3()


def test_non_radio_packet_is_not_translated():
    packet = ESP2Packet(4, ESP2ORG.ORG_RPS, bytes(4), SENDER)
    with pytest.raises(ValueError):
        packet.to_esp3()


# ---------------------------------------------------------------------------
# ESP3 -> ESP2
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rorg", "payload", "org", "data"),
    [
        (RORG.RORG_RPS, "70", ESP2ORG.ORG_RPS, "70000000"),
        (RORG.RORG_1BS, "09", ESP2ORG.ORG_1BS, "09000000"),
        (RORG.RORG_4BS, "02640009", ESP2ORG.ORG_4BS, "02640009"),
    ],
)
def test_from_esp3_builds_transmit_packet(rorg, payload, org, data):
    esp3 = ERP1Telegram(
        rorg=rorg,
        telegram_data=bytes.fromhex(payload),
        sender=EURID("01:23:45:67"),
        status=0x30,
    ).to_esp3()

    packet = ESP2Packet.from_esp3(esp3)

    assert packet.header_sequence == ESP2HeaderSequence.TRT
    assert packet.org == org
    assert packet.data == bytes.fromhex(data)
    assert packet.sender == SENDER
    assert packet.status == 0x30
    assert packet.to_bytes()[2] == 0x6B


def test_from_esp3_rejects_telegram_types_esp2_cannot_carry():
    vld = ERP1Telegram(
        rorg=RORG.RORG_VLD,
        telegram_data=bytes.fromhex("0100"),
        sender=EURID("01:23:45:67"),
    ).to_esp3()

    with pytest.raises(ValueError):
        ESP2Packet.from_esp3(vld)


def test_from_esp3_rejects_non_radio_packets():
    with pytest.raises(ValueError):
        ESP2Packet.from_esp3(ESP3Packet(ESP3PacketType.COMMON_COMMAND, b"\x08", b""))


# ---------------------------------------------------------------------------
# EnOceanSerialProtocol2
# ---------------------------------------------------------------------------


def test_protocol_emits_one_packet(protocol, gateway):
    protocol.data_received(RPS_PRESS)

    assert len(gateway.packets) == 1
    assert gateway.packets[0].packet_type == ESP3PacketType.RADIO_ERP1
    assert gateway.packets[0].data == bytes.fromhex("f670" + "01234567" + "30")
    assert gateway.packets[0].optional == b""


def test_protocol_handles_back_to_back_packets(protocol, gateway):
    protocol.data_received(RPS_PRESS + RPS_RELEASE)

    assert [packet.data[1] for packet in gateway.packets] == [0x70, 0x00]


@pytest.mark.parametrize("split", range(1, len(RPS_PRESS)))
def test_protocol_reassembles_split_packet(protocol, gateway, split):
    protocol.data_received(RPS_PRESS[:split])
    assert gateway.packets == []

    protocol.data_received(RPS_PRESS[split:])
    assert len(gateway.packets) == 1


def test_protocol_skips_garbage_before_sync(protocol, gateway):
    protocol.data_received(b"\x00\x17\xa5\x00" + RPS_PRESS)

    assert len(gateway.packets) == 1


def test_protocol_resyncs_after_corrupted_packet(protocol, gateway):
    corrupted = RPS_PRESS[:-1] + bytes([RPS_PRESS[-1] ^ 0x01])
    protocol.data_received(corrupted + RPS_RELEASE)

    assert [packet.data[1] for packet in gateway.packets] == [0x00]


def test_protocol_ignores_packets_that_are_not_received_radio_telegrams(
    protocol, gateway
):
    transmit = ESP2Packet(ESP2HeaderSequence.TRT, ESP2ORG.ORG_RPS, bytes(4), SENDER)
    protocol.data_received(transmit.to_bytes() + RPS_PRESS)

    assert len(gateway.packets) == 1


def test_protocol_ignores_unsupported_org(protocol, gateway):
    protocol.data_received(make_packet(0x0A, bytes(4)).to_bytes() + RPS_PRESS)

    assert len(gateway.packets) == 1


def test_protocol_survives_gateway_errors(protocol, gateway):
    def fail(packet: ESP3Packet) -> None:
        raise RuntimeError("boom")

    gateway.process_esp3_packet = fail
    protocol.data_received(RPS_PRESS)


def test_protocol_forwards_connection_events(protocol, gateway):
    protocol.connection_made(None)
    assert gateway.connected

    error = OSError("unplugged")
    protocol.connection_lost(error)
    assert gateway.lost == [error]
