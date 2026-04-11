"""A5-7F-3F: Eltako FSB61 motorised roller-shutter / blind actuator.

A5-7F-xx is the manufacturer-specific 4BS range (FUNC=0x7F = manufacturer-defined).
TYPE=0x3F is Eltako's identifier for the FSB roller-shutter family
(FSB14, FSB61, FSB71).

Reference: Eltako "Inhalte der Eltako-Funktelegramme" (FSB61NP-230V, p. T-15/T-17).
ORG=0x07 in Eltako ESP2 notation → RORG=0xA5 (4BS) in ESP3.

Telegram layout (4 data bytes = 32 bits, DB3…DB0):

Command telegram (gateway → FSB):
┌──────┬─────────┬──────┬──────────────────────────────────────────────────────┐
│ Name │  Bits   │  DB  │ Description                                          │
├──────┼─────────┼──────┼──────────────────────────────────────────────────────┤
│ RTS  │  0– 7   │ DB3  │ Runtime MSB (× 100 ms, used when TUNIT=1)            │
│ RTL  │  8–15   │ DB2  │ Runtime LSB (× 100 ms when TUNIT=1, or seconds       │
│      │         │      │ 1–255 when TUNIT=0; set to 0 for stop)               │
│ DIR  │ 16–23   │ DB1  │ Direction: 0x00=Stop, 0x01=Up (open), 0x02=Down      │
│ LRNB │    28   │ DB0  │ LRN bit: 0=teach-in telegram, 1=data telegram        │
│ BLK  │    29   │ DB0  │ Block: 0=release/not blocked, 1=block actor          │
│TUNIT │    30   │ DB0  │ Time unit: 0=seconds (RTL only), 1=100 ms (RTS+RTL)  │
└──────┴─────────┴──────┴──────────────────────────────────────────────────────┘

Status telegram (FSB → gateway, sent after movement completes):
┌──────┬─────────┬──────┬──────────────────────────────────────────────────────┐
│ Name │  Bits   │  DB  │ Description                                          │
├──────┼─────────┼──────┼──────────────────────────────────────────────────────┤
│ RTS  │  0– 7   │ DB3  │ Actual travel time MSB (× 100 ms)                    │
│ RTL  │  8–15   │ DB2  │ Actual travel time LSB (× 100 ms)                    │
│ DIR  │ 16–23   │ DB1  │ Direction traveled: 0x01=traveled up, 0x02=traveled  │
│      │         │      │ down                                                 │
│ LRNB │    28   │ DB0  │ LRN bit: always 1                                    │
│ BLK  │    29   │ DB0  │ Blocked: 0=not blocked (0x0A), 1=blocked (0x0E)      │
└──────┴─────────┴──────┴──────────────────────────────────────────────────────┘

Learn telegram: DB3=0xFF, DB2=0xF8, DB1=0x0D, DB0=0x80
"""

from ...semantics.entity import Entity, EntityCategory, NumberRange
from ...semantics.instructable import Instructable
from ...semantics.instructions.cover import CoverClose, CoverOpen, CoverStop
from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..message import EEPMessageType, RawEEPMessage, ValueWithContext
from ..profile import EEPDataField, Entity, SimpleProfileSpecification

# --- Entities ----------------------------------------------------------------

_COVER_ENTITY = Entity(
    id="cover",
    observables=frozenset({Observable.COVER_STATE}),
    actions=frozenset(
        {Instructable.COVER_STOP, Instructable.COVER_OPEN, Instructable.COVER_CLOSE}
    ),
)

_MAX_TRAVEL_TIME = Entity(
    id="max_travel_time",
    config_spec=NumberRange(
        min_value=1.0, max_value=255.0, step=1.0, unit="s", default=60.0
    ),
    category=EntityCategory.CONFIG,
)

_LEARN_TELEGRAM_ENTITY = Entity(
    id="learn_telegram",
    actions=frozenset({Instructable.LEARN_TELEGRAM}),
    category=EntityCategory.CONFIG,
)

# --- Semantic resolvers -------------------------------------------------------


def _resolve_cover_state(
    raw: dict, _scaled: dict, _config: dict
) -> ValueWithContext | None:
    """Derive cover state from a completed-movement status telegram.

    The FSB sends this telegram *after* movement finishes:
      DIR=1 → traveled up  → cover is now open
      DIR=2 → traveled down → cover is now closed
    """
    if raw.get("LRNB") == 0:
        return None  # teach-in telegram, ignore
    dir_val = raw.get("DIR")
    if dir_val == 1:
        return ValueWithContext(name="Cover state", value="open", unit=None)
    if dir_val == 2:
        return ValueWithContext(name="Cover state", value="closed", unit=None)
    return None


# --- Encoders ----------------------------------------------------------------


def _encode_cover_stop(_action: CoverStop) -> RawEEPMessage:
    """Encode a stop command: DIR=0, no runtime."""
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=0, description="Stop"),
    )
    msg.raw["RTS"] = 0
    msg.raw["RTL"] = 0
    msg.raw["DIR"] = 0x00
    msg.raw["LRNB"] = 1
    msg.raw["BLK"] = 0
    msg.raw["TUNIT"] = 0
    return msg


def _encode_cover_open(_action: CoverOpen, config: dict) -> RawEEPMessage:
    """Encode an 'open' (up) command with runtime from device config."""
    runtime_s = max(1, min(255, int(config.get("max_travel_time", 60))))
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=0, description="Open (up)"),
    )
    msg.raw["RTS"] = 0
    msg.raw["RTL"] = runtime_s
    msg.raw["DIR"] = 0x01
    msg.raw["LRNB"] = 1
    msg.raw["BLK"] = 0
    msg.raw["TUNIT"] = 0  # seconds
    return msg


def _encode_cover_close(_action: CoverClose, config: dict) -> RawEEPMessage:
    """Encode a 'close' (down) command with runtime from device config."""
    runtime_s = max(1, min(255, int(config.get("max_travel_time", 60))))
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=0, description="Close (down)"),
    )
    msg.raw["RTS"] = 0
    msg.raw["RTL"] = runtime_s
    msg.raw["DIR"] = 0x02
    msg.raw["LRNB"] = 1
    msg.raw["BLK"] = 0
    msg.raw["TUNIT"] = 0  # seconds
    return msg


# --- Profile specification ---------------------------------------------------

EEP_A5_7F_3F_ELTAKO_FSB = SimpleProfileSpecification(
    eep=EEP("A5-7F-3F.ELTAKO.FSB"),
    name="Eltako FSB roller-shutter / blind actuator (FSB14, FSB61, FSB71)",
    datafields=[
        EEPDataField(
            id="RTS",
            name="Runtime MSB (× 100 ms for TUNIT=1)",
            offset=0,
            size=8,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 255.0,
            unit_fn=lambda _: "",
        ),
        EEPDataField(
            id="RTL",
            name="Runtime LSB (× 100 ms for TUNIT=1) or seconds (for TUNIT=0)",
            offset=8,
            size=8,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 255.0,
            unit_fn=lambda _: "",
        ),
        EEPDataField(
            id="DIR",
            name="Direction",
            offset=16,
            size=8,
            range_enum={
                0x00: "Stop",
                0x01: "Up (open)",
                0x02: "Down (close)",
            },
        ),
        EEPDataField(
            id="LRNB",
            name="LRN bit",
            offset=28,
            size=1,
            range_enum={0: "Teach-in telegram", 1: "Data telegram"},
        ),
        EEPDataField(
            id="BLK",
            name="Block",
            offset=29,
            size=1,
            range_enum={0: "Not blocked / release", 1: "Blocked / block"},
        ),
        EEPDataField(
            id="TUNIT",
            name="Time unit",
            offset=30,
            size=1,
            range_enum={0: "Seconds", 1: "x 100 ms"},
        ),
    ],
    semantic_resolvers={Observable.COVER_STATE: _resolve_cover_state},
    observers=[scalar_factory(Observable.COVER_STATE, entity_id="cover")],
    encoders={
        Instructable.COVER_STOP: lambda a, _: _encode_cover_stop(a),
        Instructable.COVER_OPEN: _encode_cover_open,
        Instructable.COVER_CLOSE: _encode_cover_close,
    },
    entities=[_COVER_ENTITY, _MAX_TRAVEL_TIME, _LEARN_TELEGRAM_ENTITY],
    uses_addressed_sending=False,
    learn_telegram_payload=bytes([0xFF, 0xF8, 0x0D, 0x80]),
)
