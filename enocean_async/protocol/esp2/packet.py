"""EnOcean Serial Protocol Version 2 (ESP2) packet structure.

ESP2 is the serial protocol of the first EnOcean transceiver generation. It is still spoken by
some gateways, for example the Eltako FAM-USB. Every packet is exactly 14 bytes long:

    SYNC (0xA5 0x5A) | H_SEQ/LENGTH | ORG | DATA_BYTE3..0 | ID_BYTE3..0 | STATUS | CHECKSUM

- H_SEQ (upper 3 bits) tells the direction and kind of the packet, LENGTH (lower 5 bits) is the
  number of bytes that follow and is always 11.
- 1-byte telegrams (RPS, 1BS) carry their payload in DATA_BYTE3; the remaining data bytes are 0.
- CHECKSUM is the least significant byte of the sum of all bytes between SYNC and CHECKSUM.

Commands to the module and its answers use the same frame; the nine bytes after ORG then carry
the command or answer data instead of data bytes, ID and status.

This module also translates between ESP2 packets and ESP3 packets, so that everything above the
serial layer can keep working with ESP3 packets only.
"""

from dataclasses import dataclass
from enum import IntEnum

from ..erp1.rorg import RORG
from ..esp3.common_command import CommonCommandCode
from ..esp3.packet import ESP3Packet, ESP3PacketType
from ..esp3.response import ResponseCode

SYNC_BYTES = b"\xa5\x5a"

PACKET_LENGTH = 14
"""Total length of an ESP2 packet in bytes, including sync bytes and checksum."""

BODY_LENGTH = 11
"""Value of the LENGTH field: number of bytes following the H_SEQ/LENGTH byte."""


class ESP2HeaderSequence(IntEnum):
    """Direction and kind of an ESP2 packet (H_SEQ, upper 3 bits of the third byte)."""

    RRT = 0
    """Receive radio telegram: a telegram received over the air (module -> host)."""

    TRT = 3
    """Transmit radio telegram: a telegram to be sent over the air (host -> module)."""

    RMT = 4
    """Receive message telegram: an answer of the module to the host (module -> host)."""

    TCT = 5
    """Transmit command telegram: a command for the module itself (host -> module)."""


class ESP2ORG(IntEnum):
    """Radio telegram types as numbered by ESP2."""

    ORG_RPS = 0x05
    ORG_1BS = 0x06
    ORG_4BS = 0x07


class ESP2CommandCode(IntEnum):
    """Commands for the module (ORG byte of a TCT packet)."""

    RD_SW_VER = 0x4B
    """Read the software version of the module"""

    RD_IDBASE = 0x58
    """Read ID range base address"""


class ESP2MessageCode(IntEnum):
    """Answers of the module (ORG byte of an RMT packet)."""

    ERR_TX_IDRANGE = 0x22
    """The sender of a transmit request is a base address outside the ID range of the module"""

    OK = 0x58
    """The command or transmit request was accepted"""

    INF_SW_VER = 0x8C
    """Software version: 4 bytes application version followed by 4 bytes API version"""

    INF_IDBASE = 0x98
    """ID range base address in the first 4 data bytes"""


_ORG_TO_RORG: dict[int, RORG] = {
    ESP2ORG.ORG_RPS: RORG.RORG_RPS,
    ESP2ORG.ORG_1BS: RORG.RORG_1BS,
    ESP2ORG.ORG_4BS: RORG.RORG_4BS,
}

_RORG_TO_ORG: dict[int, ESP2ORG] = {rorg: org for org, rorg in _ORG_TO_RORG.items()}

_PAYLOAD_LENGTH: dict[int, int] = {
    ESP2ORG.ORG_RPS: 1,
    ESP2ORG.ORG_1BS: 1,
    ESP2ORG.ORG_4BS: 4,
}

_COMMON_COMMAND_TO_ESP2: dict[int, ESP2CommandCode] = {
    CommonCommandCode.CO_RD_IDBASE: ESP2CommandCode.RD_IDBASE,
    CommonCommandCode.CO_RD_VERSION: ESP2CommandCode.RD_SW_VER,
}


def checksum(body: bytes) -> int:
    """Calculate the ESP2 checksum: the least significant byte of the sum of all body bytes."""
    return sum(body) & 0xFF


@dataclass
class ESP2Packet:
    """
    Represents a raw ESP2 packet.

    This class does NOT interpret radio payloads.
    It only stores the ESP2 structure:
      - header sequence (H_SEQ)
      - ORG
      - the four data bytes (DATA_BYTE3..0)
      - the four ID bytes (ID_BYTE3..0)
      - status
    """

    header_sequence: int
    org: int
    data: bytes
    sender: bytes
    status: int = 0x00

    def __post_init__(self) -> None:
        if not 0 <= self.header_sequence <= 7:
            raise ValueError("ESP2 header sequence must be between 0 and 7")
        if len(self.data) != 4:
            raise ValueError(f"ESP2 data must be 4 bytes, got {len(self.data)} bytes")
        if len(self.sender) != 4:
            raise ValueError(f"ESP2 ID must be 4 bytes, got {len(self.sender)} bytes")

    def __repr__(self) -> str:
        return (
            f"ESP2Packet(h_seq={self.header_sequence}, "
            f"org=0x{self.org:02X}, "
            f"data={self.data.hex().upper()}, "
            f"sender={self.sender.hex().upper()}, "
            f"status=0x{self.status:02X})"
        )

    @property
    def body(self) -> bytes:
        """The 11 bytes between the sync bytes and the checksum."""
        return (
            bytes([(self.header_sequence << 5) | BODY_LENGTH, self.org])
            + self.data
            + self.sender
            + bytes([self.status])
        )

    @property
    def payload(self) -> bytes:
        """The 9 bytes after ORG; for commands and answers these are not data, ID and status."""
        return self.data + self.sender + bytes([self.status])

    @classmethod
    def command(cls, code: ESP2CommandCode) -> "ESP2Packet":
        """Create a command for the module (TCT) which carries no data."""
        return cls(
            header_sequence=ESP2HeaderSequence.TCT,
            org=code,
            data=bytes(4),
            sender=bytes(4),
        )

    def to_bytes(self) -> bytes:
        """Serialize the ESP2Packet to bytes, including sync bytes and checksum."""
        body = self.body
        return SYNC_BYTES + body + bytes([checksum(body)])

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ESP2Packet":
        """Parse exactly one ESP2 packet (14 bytes, including sync bytes and checksum)."""
        if len(raw) != PACKET_LENGTH:
            raise ValueError(
                f"ESP2 packet must be {PACKET_LENGTH} bytes, got {len(raw)} bytes"
            )
        if raw[:2] != SYNC_BYTES:
            raise ValueError("ESP2 packet does not start with the sync bytes")

        body = raw[2:13]
        if body[0] & 0x1F != BODY_LENGTH:
            raise ValueError(f"Unexpected ESP2 length field: {body[0] & 0x1F}")
        if checksum(body) != raw[13]:
            raise ValueError("ESP2 checksum mismatch")

        return cls(
            header_sequence=body[0] >> 5,
            org=body[1],
            data=bytes(body[2:6]),
            sender=bytes(body[6:10]),
            status=body[10],
        )

    def to_esp3(self) -> ESP3Packet:
        """Translate this packet into the equivalent ESP3 packet.

        - A radio telegram (RRT, TRT) becomes a RADIO_ERP1 packet. ESP2 carries neither signal
          strength nor a destination address, so the resulting packet has no optional data.
        - An answer of the module (RMT) becomes a RESPONSE packet. An answer this library does
          not know is reported with return code ERROR.
        """
        if self.header_sequence == ESP2HeaderSequence.RMT:
            return self.__answer_to_esp3()

        if self.header_sequence not in (ESP2HeaderSequence.RRT, ESP2HeaderSequence.TRT):
            raise ValueError(
                f"ESP2 packet with H_SEQ {self.header_sequence} has no ESP3 equivalent"
            )

        rorg = _ORG_TO_RORG.get(self.org)
        if rorg is None:
            raise ValueError(f"Unsupported ESP2 ORG: 0x{self.org:02X}")

        payload = self.data[: _PAYLOAD_LENGTH[self.org]]
        return ESP3Packet(
            packet_type=ESP3PacketType.RADIO_ERP1,
            data=bytes([rorg]) + payload + self.sender + bytes([self.status]),
            optional=b"",
        )

    def __answer_to_esp3(self) -> ESP3Packet:
        """Translate an answer of the module (RMT) into an ESP3 RESPONSE packet."""
        match self.org:
            case ESP2MessageCode.OK:
                data = bytes([ResponseCode.OK])
            case ESP2MessageCode.INF_IDBASE:
                data = bytes([ResponseCode.OK]) + self.payload[:4]
            case ESP2MessageCode.INF_SW_VER:
                data = bytes([ResponseCode.OK]) + self.payload[:8]
            case _:
                data = bytes([ResponseCode.ERROR])

        return ESP3Packet(packet_type=ESP3PacketType.RESPONSE, data=data, optional=b"")

    @classmethod
    def from_esp3(cls, packet: ESP3Packet) -> "ESP2Packet":
        """Translate an ESP3 packet from the host into the ESP2 packet to be sent to the module.

        - A RADIO_ERP1 packet becomes a transmit request (TRT). ESP2 can only carry RPS, 1BS and
          4BS telegrams. Optional data (destination address, signal strength, security level)
          has no ESP2 equivalent and is dropped.
        - A COMMON_COMMAND packet becomes a command (TCT), if ESP2 has an equivalent command.

        Raises:
            ValueError: If the packet cannot be expressed in ESP2.
        """
        if packet.packet_type == ESP3PacketType.COMMON_COMMAND:
            code = _COMMON_COMMAND_TO_ESP2.get(packet.data[0]) if packet.data else None
            if code is None:
                raise ValueError(
                    f"ESP3 common command {packet.data.hex().upper()} has no ESP2 equivalent"
                )
            return cls.command(code)

        if packet.packet_type != ESP3PacketType.RADIO_ERP1:
            raise ValueError(
                f"ESP3 packet of type {packet.packet_type.name} cannot be sent via ESP2"
            )
        if len(packet.data) < 6:
            raise ValueError(f"ERP1 telegram too short: {len(packet.data)} bytes")

        org = _RORG_TO_ORG.get(packet.data[0])
        if org is None:
            raise ValueError(
                f"RORG 0x{packet.data[0]:02X} cannot be sent via ESP2 (only RPS, 1BS and 4BS)"
            )

        payload = packet.data[1:-5]
        if len(payload) != _PAYLOAD_LENGTH[org]:
            raise ValueError(
                f"{org.name[4:]} telegram data must be {_PAYLOAD_LENGTH[org]} byte(s), got {len(payload)} bytes"
            )

        return cls(
            header_sequence=ESP2HeaderSequence.TRT,
            org=org,
            data=payload.ljust(4, b"\x00"),
            sender=packet.data[-5:-1],
            status=packet.data[-1],
        )
