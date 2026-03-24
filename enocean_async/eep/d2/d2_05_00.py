"""D2-05-00: Blinds control for position and angle, type 0x00."""

from ...semantics.entity import EntityCategory, EnumOptions
from ...semantics.instructable import Instructable
from ...semantics.instructions.cover import (
    CoverClose,
    CoverOpen,
    CoverQueryPositionAndAngle,
    CoverSetPositionAndAngle,
    CoverStop,
)
from ...semantics.observable import Observable
from ...semantics.observers.cover import cover_factory
from ..id import EEP
from ..message import EEPMessageType, RawEEPMessage
from ..profile import EEPDataField, EEPSpecification, EEPTelegram, Entity

# Shared CMD field definitions.
# cmd_offset=-4, cmd_size=4: the CMD nibble occupies the last 4 bits of each telegram's buffer.
# Absolute offset = ceil(max_non_cmd_bit / 8) * 8 - 4.
#   Telegrams 1 & 4 have data through bit 28 → 4-byte buffer → CMD at offset 28.
#   Telegrams 2 & 3 have data through bit  4 → 4-byte buffer → CMD at offset  4.
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
    chn_val = int(action.entity_id) if action.entity_id.isdigit() else 15
    msg.raw["CHN"] = chn_val
    return msg


def _encode_stop(action: CoverStop) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=2, description="Stop"),
    )
    chn_val = int(action.entity_id) if action.entity_id.isdigit() else 15
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
    chn_val = int(action.entity_id) if action.entity_id.isdigit() else 15
    msg.raw["CHN"] = chn_val
    return msg


EEP_D2_05_00 = EEPSpecification(
    eep=EEP("D2-05-00"),
    name="Blinds control for position and angle, type 0x00",
    cmd_size=4,
    cmd_offset=-4,
    telegrams={
        1: EEPTelegram(
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
                EEPDataField(
                    id="CHN",
                    name="Channel",
                    offset=24,
                    size=4,
                    range_enum={
                        0: "Channel 1",
                        1: "Channel 2",
                        2: "Channel 3",
                        3: "Channel 4",
                        15: "All channels",
                    },
                ),
                _CMD_AT_OFFSET28,
            ],
        ),
        2: EEPTelegram(
            name="Stop",
            datafields=[
                EEPDataField(
                    id="CHN",
                    name="Channel",
                    offset=0,
                    size=4,
                    range_enum={
                        0: "Channel 1",
                        1: "Channel 2",
                        2: "Channel 3",
                        3: "Channel 4",
                        15: "All channels",
                    },
                ),
                _CMD_AT_OFFSET4,
            ],
        ),
        3: EEPTelegram(
            name="Query position and angle",
            datafields=[
                EEPDataField(
                    id="CHN",
                    name="Channel",
                    offset=0,
                    size=4,
                    range_enum={
                        0: "Channel 1",
                        1: "Channel 2",
                        2: "Channel 3",
                        3: "Channel 4",
                        15: "All channels",
                    },
                ),
                _CMD_AT_OFFSET4,
            ],
        ),
        4: EEPTelegram(
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
                EEPDataField(
                    id="CHN",
                    name="Channel",
                    offset=24,
                    size=4,
                    range_enum={
                        0: "Channel 1",
                        1: "Channel 2",
                        2: "Channel 3",
                        3: "Channel 4",
                    },
                ),
                _CMD_AT_OFFSET28,
            ],
        ),
    },
    observers=[cover_factory()],
    encoders={
        Instructable.COVER_SET_POSITION_AND_ANGLE: lambda a,
        _: _encode_set_position_and_angle(a),
        Instructable.COVER_STOP: lambda a, _: _encode_stop(a),
        Instructable.COVER_OPEN: lambda a, _: _encode_open(a),
        Instructable.COVER_CLOSE: lambda a, _: _encode_close(a),
        Instructable.COVER_QUERY_POSITION_AND_ANGLE: lambda a,
        _: _encode_query_position_and_angle(a),
    },
    entities=[
        Entity(
            id="cover",
            observables=frozenset(
                {Observable.POSITION, Observable.ANGLE, Observable.COVER_STATE}
            ),
            actions=frozenset(
                {
                    Instructable.COVER_SET_POSITION_AND_ANGLE,
                    Instructable.COVER_STOP,
                    Instructable.COVER_OPEN,
                    Instructable.COVER_CLOSE,
                    Instructable.COVER_QUERY_POSITION_AND_ANGLE,
                }
            ),
        ),
        Entity(
            id="query_position",
            actions=frozenset({Instructable.COVER_QUERY_POSITION_AND_ANGLE}),
        ),
        Entity(
            id="repositioning_mode",
            option_spec=EnumOptions(
                options=("direct", "up_first", "down_first"), default="direct"
            ),
            category=EntityCategory.CONFIG,
        ),
    ],
)
