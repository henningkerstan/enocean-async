"""D2-05: Blinds control for position and angle.

CMD 1–4 (Go to position and angle, Stop, Query, Reply) share the same bit
layout across all TYPE variants; only the channel count and support for
CMD 5 (Set parameters) differ per type:

  Type 0x00 — 1 channel,  Set parameters supported
  Type 0x01 — 4 channels, Set parameters supported
  Type 0x02 — 1 channel,  Set parameters not supported
"""

from ...semantics.entity import EntityCategory, EnumOptions
from ...semantics.instructable import Instructable
from ...semantics.instructions.cover import (
    CoverClose,
    CoverOpen,
    CoverQueryPositionAndAngle,
    CoverSetParameters,
    CoverSetPositionAndAngle,
    CoverStop,
)
from ...semantics.observable import Observable
from ...semantics.observers.cover import cover_factory
from ..id import EEP
from ..message import EEPMessageType, RawEEPMessage
from ..profile import EEPDataField, EEPSpecification, EEPTelegram, Entity
from ._util import channel_from_entity_id

# ---------------------------------------------------------------------------
# Shared field definitions
# ---------------------------------------------------------------------------

_CHN_ENUM_ALL = {
    0: "Channel 1",
    1: "Channel 2",
    2: "Channel 3",
    3: "Channel 4",
    15: "All channels",
}
_CHN_ENUM_SINGLE = {
    0: "Channel 1",
    1: "Channel 2",
    2: "Channel 3",
    3: "Channel 4",
}


def _chn(offset: int, *, allow_all: bool = True) -> EEPDataField:
    """Channel address field. Reply telegrams never carry CHN=15 (allow_all=False)."""
    return EEPDataField(
        id="CHN",
        name="Channel",
        offset=offset,
        size=4,
        range_enum=_CHN_ENUM_ALL if allow_all else _CHN_ENUM_SINGLE,
    )


# cmd_offset=-4, cmd_size=4: the CMD nibble occupies the last 4 bits of each telegram's buffer.
# Absolute offset = ceil(max_non_cmd_bit / 8) * 8 - 4.
#   Telegrams 1 & 4 have data through bit 28 → 4-byte buffer → CMD at offset 28.
#   Telegrams 2 & 3 have data through bit  4 → 1-byte buffer → CMD at offset  4.
#   Telegram  5     has data through bit 36 → 5-byte buffer → CMD at offset 36.
_CMD_AT_OFFSET28 = EEPDataField(
    id="CMD",
    name="Command",
    offset=28,
    size=4,
    range_enum={1: "Go to position and angle", 4: "Reply position and angle"},
)
_CMD_AT_OFFSET4 = EEPDataField(
    id="CMD",
    name="Command",
    offset=4,
    size=4,
    range_enum={2: "Stop", 3: "Query position and angle"},
)
_CMD_AT_OFFSET36 = EEPDataField(
    id="CMD", name="Command", offset=36, size=4, range_enum={5: "Set parameters"}
)


# ---------------------------------------------------------------------------
# Action encoders
# ---------------------------------------------------------------------------


def _encode_set_position_and_angle(action: CoverSetPositionAndAngle) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=1, description="Go to position and angle"),
    )
    # 0–100 = percent directly; 127 = "do not change" sentinel; 101–126 unused.
    msg.raw["POS"] = (
        127 if action.position is None else max(0, min(100, action.position))
    )
    msg.raw["ANG"] = 127 if action.angle is None else max(0, min(100, action.angle))
    msg.raw["REPO"] = action.repositioning_mode
    msg.raw["LOCK"] = action.lock_mode
    chn_val = channel_from_entity_id(action.entity_id, default=15)
    msg.raw["CHN"] = chn_val
    return msg


def _encode_stop(action: CoverStop) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=2, description="Stop"),
    )
    chn_val = channel_from_entity_id(action.entity_id, default=15)
    msg.raw["CHN"] = chn_val
    return msg


def _encode_open(action: CoverOpen) -> RawEEPMessage:
    """Open fully: encode as go-to-position 0%, keep current angle."""
    return _encode_set_position_and_angle(
        CoverSetPositionAndAngle(position=0, angle=None, entity_id=action.entity_id)
    )


def _encode_close(action: CoverClose) -> RawEEPMessage:
    """Close fully: encode as go-to-position 100%, keep current angle."""
    return _encode_set_position_and_angle(
        CoverSetPositionAndAngle(position=100, angle=None, entity_id=action.entity_id)
    )


def _encode_query_position_and_angle(
    action: CoverQueryPositionAndAngle,
) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=3, description="Query position and angle"),
    )
    chn_val = channel_from_entity_id(action.entity_id, default=15)
    msg.raw["CHN"] = chn_val
    return msg


def _encode_set_parameters(action: CoverSetParameters) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=5, description="Set parameters"),
    )
    if action.vertical_run_time_ms is None:
        vert_val = 32767
    else:
        vert_val = max(500, min(30000, round(action.vertical_run_time_ms / 10)))
    msg.raw["VERT"] = vert_val

    if action.rotation_time_ms is None:
        rot_val = 255
    elif action.rotation_time_ms == 0:
        rot_val = 0
    else:
        rot_val = max(1, min(254, round(action.rotation_time_ms / 10)))
    msg.raw["ROT"] = rot_val

    msg.raw["AA"] = action.alarm_action
    chn_val = channel_from_entity_id(action.entity_id, default=15)
    msg.raw["CHN"] = chn_val
    return msg


# ---------------------------------------------------------------------------
# Telegram definitions
# ---------------------------------------------------------------------------

_TELEGRAM_GOTO = EEPTelegram(
    name="Go to position and angle",
    datafields=[
        EEPDataField(
            id="POS",
            name="Vertical position",
            offset=1,
            size=7,
            range_min=0,
            range_max=127,
            unit_fn=lambda _: "%",
            observable=Observable.POSITION,
        ),
        EEPDataField(
            id="ANG",
            name="Rotation angle",
            offset=9,
            size=7,
            range_min=0,
            range_max=127,
            unit_fn=lambda _: "%",
            observable=Observable.ANGLE,
        ),
        EEPDataField(
            id="REPO",
            name="Repositioning mode",
            offset=17,
            size=3,
            range_enum={
                0: "Directly to target POS/ANG",
                1: "Up, then to target POS/ANG",
                2: "Down, then to target POS/ANG",
                3: "Reserved",
                4: "Reserved",
                5: "Reserved",
                6: "Reserved",
                7: "Reserved",
            },
        ),
        EEPDataField(
            id="LOCK",
            name="Set locking mode",
            offset=21,
            size=3,
            range_enum={
                0: "No change",
                1: "Set blockage mode",
                2: "Set alarm mode",
                3: "Reserved",
                4: "Reserved",
                5: "Reserved",
                6: "Reserved",
                7: "Unblock",
            },
        ),
        _chn(24),
        _CMD_AT_OFFSET28,
    ],
)

_TELEGRAM_STOP = EEPTelegram(
    name="Stop",
    datafields=[
        _chn(0),
        _CMD_AT_OFFSET4,
    ],
)

_TELEGRAM_QUERY = EEPTelegram(
    name="Query position and angle",
    datafields=[
        _chn(0),
        _CMD_AT_OFFSET4,
    ],
)

_TELEGRAM_REPLY = EEPTelegram(
    name="Reply position and angle",
    datafields=[
        EEPDataField(
            id="POS",
            name="Vertical position",
            offset=1,
            size=7,
            unit_fn=lambda _: "%",
            observable=Observable.POSITION,
        ),
        EEPDataField(
            id="ANG",
            name="Rotation angle",
            offset=9,
            size=7,
            unit_fn=lambda _: "%",
            observable=Observable.ANGLE,
        ),
        EEPDataField(
            id="LOCK",
            name="Locking modes",
            offset=21,
            size=3,
            range_enum={
                0: "Normal (no lock)",
                1: "Blockage mode",
                2: "Alarm mode",
                3: "Reserved",
                4: "Reserved",
                5: "Reserved",
                6: "Reserved",
                7: "Reserved",
            },
        ),
        _chn(24, allow_all=False),
        _CMD_AT_OFFSET28,
    ],
)

_TELEGRAM_SET_PARAMETERS = EEPTelegram(
    name="Set parameters",
    datafields=[
        EEPDataField(
            id="VERT",
            name="Set vertical run time",
            offset=1,
            size=15,
            unit_fn=lambda _: "ms",
        ),
        EEPDataField(
            id="ROT",
            name="Set rotation time",
            offset=16,
            size=8,
            unit_fn=lambda _: "ms",
        ),
        EEPDataField(
            id="AA",
            name="Set alarm action",
            offset=29,
            size=3,
            range_enum={
                0: "No action",
                1: "Immediate stop",
                2: "Go up (0%)",
                3: "Go down (100%)",
                4: "Reserved",
                5: "Reserved",
                6: "Reserved",
                7: "No change",
            },
        ),
        _chn(32),
        _CMD_AT_OFFSET36,
    ],
)

_COVER_ACTIONS = frozenset(
    {
        Instructable.COVER_SET_POSITION_AND_ANGLE,
        Instructable.COVER_STOP,
        Instructable.COVER_OPEN,
        Instructable.COVER_CLOSE,
        Instructable.COVER_QUERY_POSITION_AND_ANGLE,
    }
)


# ---------------------------------------------------------------------------
# Entities / observers
# ---------------------------------------------------------------------------


def _entities(channels: int, *, supports_set_parameters: bool) -> list[Entity]:
    actions = (
        _COVER_ACTIONS | {Instructable.COVER_SET_PARAMETERS}
        if supports_set_parameters
        else _COVER_ACTIONS
    )
    cover_observables = frozenset(
        {Observable.POSITION, Observable.ANGLE, Observable.COVER_STATE}
    )

    if channels == 1:
        result = [Entity(id="cover", observables=cover_observables, actions=actions)]
    else:
        result = [
            Entity(id=f"ch{n}_cover", observables=cover_observables, actions=actions)
            for n in range(1, channels + 1)
        ]

    result.append(
        Entity(
            id="query_position",
            actions=frozenset({Instructable.COVER_QUERY_POSITION_AND_ANGLE}),
        )
    )
    result.append(
        Entity(
            id="repositioning_mode",
            config_spec=EnumOptions(
                options=("direct", "up_first", "down_first"), default="direct"
            ),
            category=EntityCategory.CONFIG,
        )
    )
    return result


def _observers(channels: int) -> list:
    if channels == 1:
        return [cover_factory()]
    return [cover_factory(channel=n) for n in range(channels)]


# ---------------------------------------------------------------------------
# EEPSpecification factory + all type variants
# ---------------------------------------------------------------------------
def _spec(
    type_id: int,
    name: str,
    *,
    channels: int = 1,
    supports_set_parameters: bool = True,
) -> EEPSpecification:
    telegrams = {
        1: _TELEGRAM_GOTO,
        2: _TELEGRAM_STOP,
        3: _TELEGRAM_QUERY,
        4: _TELEGRAM_REPLY,
    }
    encoders = {
        Instructable.COVER_SET_POSITION_AND_ANGLE: lambda a, _: (
            _encode_set_position_and_angle(a)
        ),
        Instructable.COVER_STOP: lambda a, _: _encode_stop(a),
        Instructable.COVER_OPEN: lambda a, _: _encode_open(a),
        Instructable.COVER_CLOSE: lambda a, _: _encode_close(a),
        Instructable.COVER_QUERY_POSITION_AND_ANGLE: lambda a, _: (
            _encode_query_position_and_angle(a)
        ),
    }
    if supports_set_parameters:
        telegrams[5] = _TELEGRAM_SET_PARAMETERS
        encoders[Instructable.COVER_SET_PARAMETERS] = lambda a, _: (
            _encode_set_parameters(a)
        )

    return EEPSpecification(
        eep=EEP(f"D2-05-{type_id:02X}"),
        name=f"Blinds control for position and angle – {name}",
        cmd_size=4,
        cmd_offset=-4,
        telegrams=telegrams,
        observers=_observers(channels),
        encoders=encoders,
        entities=_entities(channels, supports_set_parameters=supports_set_parameters),
    )


EEP_D2_05_00 = _spec(0x00, "Type 0x00 – 1 channel", channels=1)
EEP_D2_05_01 = _spec(0x01, "Type 0x01 – 4 channels", channels=4)
EEP_D2_05_02 = _spec(
    0x02,
    "Type 0x02 – 1 channel, reduced command set",
    channels=1,
    supports_set_parameters=False,
)
