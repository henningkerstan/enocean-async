from dataclasses import dataclass, field
from typing import Any, Dict, NamedTuple

from ..address import EURID, Address, BaseAddress, BroadcastAddress
from ..eep.id import EEP
from ..semantics.observable import Observable


class ValueWithContext(NamedTuple):
    """A lightweight container for semantic entity values."""

    value: Any
    """The interpreted/scaled value."""

    unit: str | None = None
    """The unit of the value (e.g., '°C', '%', 'lx')."""

    name: str = ""
    """A human-readable name for the value (e.g. 'Temperature', 'Occupancy').

    Populated from ``EEPDataField.name`` during decode, or set explicitly by semantic resolvers.
    Empty string if not populated.
    """


@dataclass
class EEPMessageType:
    """Representation of an EEP message type."""

    id: int
    """A unique identifier for the message type."""

    description: str
    """A human-readable description of the message type."""


@dataclass
class RawEEPMessage:
    """Encode-path message: envelope fields plus raw field values.

    Produced by instruction encoders and consumed by ``EEPHandler.encode()``.
    Contains only the information needed to write bits onto the wire — no scaling
    or semantic interpretation.
    """

    sender: EURID | BaseAddress | None
    """Sender address. Set to ``None`` by encoders; filled in by the gateway before encoding."""

    destination: Address = BroadcastAddress()
    """Destination address. Differs from broadcast only for addressed telegrams (e.g. VLD)."""

    eep: EEP | None = None
    """EEP identifier, if known."""

    rssi: int | None = None
    """Received signal strength. Always ``None`` on the encode path."""

    message_type: EEPMessageType | None = None
    """Telegram sub-type within the EEP (selects the CMD value). ``None`` for single-telegram EEPs."""

    raw: Dict[str, int] = field(default_factory=dict)
    """Raw field values keyed by EEP field ID (e.g. ``'POS'``, ``'R1'``).

    Values are plain integers as they appear on the wire — no scaling applied.
    """


@dataclass
class EEPMessage(RawEEPMessage):
    """Decode-path message: extends ``RawEEPMessage`` with scaled field values and semantic entities.

    Produced by ``EEPHandler.decode()``. Not intended to be constructed manually.
    """

    decoded: Dict[str, ValueWithContext] = field(default_factory=dict)
    """Per-field decoded values keyed by EEP field ID.

    Each entry holds the scaled or enum-resolved value for that field together
    with its unit (e.g. ``ValueWithContext(value=23.4, unit='°C', name='Temperature')``).
    Populated in parallel with ``raw`` during decode.
    """

    values: Dict[Observable, ValueWithContext] = field(default_factory=dict)
    """Semantic entity values keyed by ``Observable``.

    Populated from ``decoded`` via ``EEPDataField.observable`` annotations and
    semantic resolvers. These are the values that observers and integrations consume.
    """

    def __repr__(self) -> str:
        msg = f"EEPMessage(sender={str(self.sender)}, eep={self.eep}, message_type={self.message_type if self.message_type else 'default'}"
        if self.destination is not None and not self.destination.is_broadcast():
            msg += f", destination={str(self.destination)}"

        msg += f", raw={self.raw}, decoded={self.decoded}, values={self.values})"
        return msg
