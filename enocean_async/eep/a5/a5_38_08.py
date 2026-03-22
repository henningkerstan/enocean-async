"""A5-38-08: Central command - gateway."""

from ...semantics.entity import Entity, EntityCategory, EnumOptions, NumberRange
from ...semantics.instructable import Instructable
from ...semantics.instructions.cover import (
    CoverClose,
    CoverOpen,
    CoverSetPositionAndAngle,
    CoverStop,
)
from ...semantics.instructions.dimmer import Dim, Switch
from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..message import EEPMessageType, RawEEPMessage, ValueWithContext
from ..profile import EEPDataField, EEPSpecification, EEPTelegram


def _resolve_edim(raw: dict, _scaled: dict) -> ValueWithContext | None:
    """Convert EDIM raw value to a percentage using EDIMR to select the scale."""
    edim = raw.get("EDIM")
    edimr = raw.get("EDIMR")
    if edim is None or edimr is None:
        return None
    # EDIMR=1 (relative): raw 0–100 maps directly to 0–100 %
    # EDIMR=0 (absolute): raw 0–255 maps to 0–100 %
    if edimr == 1:
        pct = float(edim)
    else:
        pct = edim * 100.0 / 255.0
    return ValueWithContext(name="Dimming value", value=round(pct, 1), unit="%")


def _encode_switch(action: Switch) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=1, description="Switching"),
    )
    msg.raw["TIM"] = max(0, min(65535, action.time))
    msg.raw["LCK"] = int(action.lock)
    msg.raw["DEL"] = int(action.delay)
    msg.raw["SW"] = int(action.switch_on)
    msg.raw["LRNB"] = 1  # data telegram (not teach-in)
    return msg


def _encode_dim(action: Dim) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=2, description="Dimming"),
    )
    # dim_value is 0–100 %.
    # Relative (EDIMR=1): raw 0–100 maps directly.
    # Absolute (EDIMR=0): raw 0–255 maps to 0–100 %.
    if action.use_relative:
        msg.raw["EDIM"] = max(0, min(100, round(action.dim_value)))
        msg.raw["EDIMR"] = 1
    else:
        msg.raw["EDIM"] = max(0, min(255, round(action.dim_value / 100.0 * 255)))
        msg.raw["EDIMR"] = 0
    msg.raw["RMP"] = action.ramp_time
    msg.raw["STR"] = int(action.store)
    msg.raw["SW"] = int(action.switch_on)
    msg.raw["LRNB"] = 1  # data telegram (not teach-in)
    return msg


def _cover_msg(func_id: int) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=7, description="Shutters / Blinds"),
    )
    msg.raw["FUNC"] = func_id
    msg.raw["SSF"] = 1
    return msg


def _encode_cover_stop(_action: CoverStop) -> RawEEPMessage:
    """Encode FUNC=1 (stop)."""
    msg = _cover_msg(1)
    msg.raw["P1"] = 0
    msg.raw["P2"] = 0
    msg.raw["PAF"] = 0
    return msg


def _encode_cover_open(_action: CoverOpen) -> RawEEPMessage:
    """Encode FUNC=2 (open fully)."""
    msg = _cover_msg(2)
    msg.raw["P1"] = 0
    msg.raw["P2"] = 0
    msg.raw["PAF"] = 0
    return msg


def _encode_cover_close(_action: CoverClose) -> RawEEPMessage:
    """Encode FUNC=3 (close fully)."""
    msg = _cover_msg(3)
    msg.raw["P1"] = 0
    msg.raw["P2"] = 0
    msg.raw["PAF"] = 0
    return msg


def _encode_set_cover_position(action: CoverSetPositionAndAngle) -> RawEEPMessage:
    """Encode FUNC=4 (drive to position with angle).

    P1 = position in % (0–100); None → 0.
    P2: Bit7 = sign (always 0 = positive), Bit6-0 = round(angle_pct * 45 / 100)
        mapping 0–100 % → 0–45 (representing 0–90°).
    angle=None → P2=0 (neutral).
    """
    msg = _cover_msg(4)
    p1 = max(0, min(100, action.position)) if action.position is not None else 0
    angle_pct = max(0, min(100, action.angle)) if action.angle is not None else 0
    p2 = round(angle_pct * 45 / 100) & 0x7F  # sign bit = 0 (positive)
    msg.raw["P1"] = p1
    msg.raw["P2"] = p2
    msg.raw["PAF"] = 1
    return msg


_DIMMER_ENTITY = Entity(
    id="light",
    observables=frozenset({Observable.OUTPUT_VALUE}),
    actions=frozenset({Instructable.DIM, Instructable.SWITCH}),
)

_DIM_MODE_SELECT = Entity(
    id="dimming_mode",
    option_spec=EnumOptions(options=("relative", "absolute")),
    category=EntityCategory.CONFIG,
)

_MIN_BRIGHTNESS = Entity(
    id="min_brightness",
    option_spec=NumberRange(min_value=0.0, max_value=100.0, step=1.0, unit="%"),
    category=EntityCategory.CONFIG,
)

_MAX_BRIGHTNESS = Entity(
    id="max_brightness",
    option_spec=NumberRange(min_value=0.0, max_value=100.0, step=1.0, unit="%"),
    category=EntityCategory.CONFIG,
)

# Shared LRN bit field (4BS data telegram indicator)
_LRNB = EEPDataField(
    id="LRNB",
    name="LRN Bit",
    offset=28,
    size=1,
    range_enum={0: "Teach-in telegram", 1: "Data telegram"},
)


EEP_A5_38_08 = EEPSpecification(
    eep=EEP("A5-38-08"),
    name="Central command - gateway",
    cmd_size=8,
    cmd_offset=0,
    telegrams={
        1: EEPTelegram(
            name="Switching",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=0,
                    size=8,
                    range_enum={1: "Switching"},
                ),
                EEPDataField(
                    id="TIM",
                    name="Time",
                    offset=8,
                    size=16,
                    range_min=0,
                    range_max=65535,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 6553.5,
                    unit_fn=lambda _: "s",
                ),
                _LRNB,
                EEPDataField(
                    id="LCK",
                    name="Lock",
                    offset=29,
                    size=1,
                    range_enum={0: "Unlock", 1: "Lock"},
                ),
                EEPDataField(
                    id="DEL",
                    name="Delay or duration",
                    offset=30,
                    size=1,
                    range_enum={0: "Duration", 1: "Delay"},
                ),
                EEPDataField(
                    id="SW",
                    name="Switching command",
                    offset=31,
                    size=1,
                    range_enum={0: "Off", 1: "On"},
                ),
            ],
        ),
        2: EEPTelegram(
            name="Dimming",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=0,
                    size=8,
                    range_enum={2: "Dimming"},
                ),
                EEPDataField(
                    id="EDIM",
                    name="Dimming value",
                    offset=8,
                    size=8,
                    range_min=0,
                    range_max=255,
                    scale_min_fn=lambda _: None,  # scaling done by semantic resolver
                ),
                EEPDataField(
                    id="RMP",
                    name="Ramping time",
                    offset=16,
                    size=8,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 255.0,
                    unit_fn=lambda _: "s",
                ),
                _LRNB,
                EEPDataField(
                    id="EDIMR",
                    name="Dimming range",
                    offset=29,
                    size=1,
                    range_enum={
                        0: "Absolute",
                        1: "Relative",
                    },
                ),
                EEPDataField(
                    id="STR",
                    name="Store final value",
                    offset=30,
                    size=1,
                    range_enum={
                        0: "No",
                        1: "Yes",
                    },
                ),
                EEPDataField(
                    id="SW",
                    name="Switching command",
                    offset=31,
                    size=1,
                    range_enum={
                        0: "Off",
                        1: "On",
                    },
                ),
            ],
        ),
        3: EEPTelegram(
            name="Setpoint shift",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=0,
                    size=8,
                    range_enum={3: "Setpoint shift"},
                ),
                EEPDataField(
                    id="SP",
                    name="Setpoint shift",
                    offset=16,
                    size=8,
                    range_min=0,
                    range_max=255,
                    scale_min_fn=lambda _: -12.7,
                    scale_max_fn=lambda _: 12.8,
                    unit_fn=lambda _: "K",
                ),
                _LRNB,
            ],
        ),
        4: EEPTelegram(
            name="Basic setpoint",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=0,
                    size=8,
                    range_enum={4: "Basic setpoint"},
                ),
                EEPDataField(
                    id="BSP",
                    name="Basic setpoint",
                    offset=16,
                    size=8,
                    range_min=0,
                    range_max=255,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 51.2,
                    unit_fn=lambda _: "°C",
                ),
                _LRNB,
            ],
        ),
        5: EEPTelegram(
            name="Control variable",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=0,
                    size=8,
                    range_enum={5: "Control variable"},
                ),
                EEPDataField(
                    id="CVOV",
                    name="Control variable override",
                    offset=16,
                    size=8,
                    range_min=0,
                    range_max=255,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 100.0,
                    unit_fn=lambda _: "%",
                ),
                EEPDataField(
                    id="CM",
                    name="Controller mode",
                    offset=25,
                    size=2,
                    range_enum={
                        0: "Automatic",
                        1: "Heating",
                        2: "Cooling",
                        3: "Off",
                    },
                ),
                EEPDataField(
                    id="CS",
                    name="Controller state",
                    offset=27,
                    size=1,
                    range_enum={0: "Automatic", 1: "Override"},
                ),
                _LRNB,
                EEPDataField(
                    id="ENHO",
                    name="Energy hold off",
                    offset=29,
                    size=1,
                    range_enum={0: "Normal", 1: "Energy holdoff / Dew point"},
                ),
                EEPDataField(
                    id="RMOCC",
                    name="Room occupancy",
                    offset=30,
                    size=2,
                    range_enum={0: "Occupied", 1: "Unoccupied", 2: "Standby"},
                ),
            ],
        ),
        6: EEPTelegram(
            name="Fan stage",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=0,
                    size=8,
                    range_enum={6: "Fan stage"},
                ),
                EEPDataField(
                    id="FO",
                    name="Fan stage override",
                    offset=16,
                    size=8,
                    range_enum={
                        0: "Stage 0",
                        1: "Stage 1",
                        2: "Stage 2",
                        3: "Stage 3",
                        255: "Auto",
                    },
                ),
                _LRNB,
            ],
        ),
        7: EEPTelegram(
            name="Shutters / Blinds",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=0,
                    size=8,
                    range_enum={7: "Shutters / Blinds"},
                ),
                EEPDataField(
                    id="P1",
                    name="Parameter 1",
                    offset=8,
                    size=8,
                    range_min=0,
                    range_max=255,
                ),
                EEPDataField(
                    id="P2",
                    name="Parameter 2",
                    offset=16,
                    size=8,
                    range_min=0,
                    range_max=255,
                ),
                EEPDataField(
                    id="FUNC",
                    name="Function",
                    offset=24,
                    size=4,
                    range_enum={
                        0: "Status request",
                        1: "Stop",
                        2: "Open",
                        3: "Close",
                        4: "Drive to position",
                        5: "Open for time",
                        6: "Close for time",
                        7: "Set runtime parameters",
                        8: "Set angle configuration",
                        9: "Set min/max values",
                        10: "Set slat angles",
                        11: "Set position logic",
                    },
                ),
                _LRNB,
                EEPDataField(
                    id="SSF",
                    name="Send status flag",
                    offset=29,
                    size=1,
                    range_enum={0: "Send new status", 1: "Send no status"},
                ),
                EEPDataField(
                    id="PAF",
                    name="Position and angle availability flag",
                    offset=30,
                    size=1,
                    range_enum={0: "Not available", 1: "Available"},
                ),
                EEPDataField(
                    id="SMF",
                    name="Service mode flag",
                    offset=31,
                    size=1,
                    range_enum={0: "Normal", 1: "Service mode"},
                ),
            ],
        ),
    },
    entities=[_DIMMER_ENTITY, _DIM_MODE_SELECT, _MIN_BRIGHTNESS, _MAX_BRIGHTNESS],
    observers=[scalar_factory(Observable.OUTPUT_VALUE, entity_id="light")],
    semantic_resolvers={
        Observable.OUTPUT_VALUE: _resolve_edim,
    },
    encoders={
        Instructable.SWITCH: _encode_switch,
        Instructable.DIM: _encode_dim,
        Instructable.COVER_STOP: _encode_cover_stop,
        Instructable.COVER_OPEN: _encode_cover_open,
        Instructable.COVER_CLOSE: _encode_cover_close,
        Instructable.COVER_SET_POSITION_AND_ANGLE: _encode_set_cover_position,
    },
    uses_addressed_sending=False,
)
