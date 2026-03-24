"""A5-38-08: Central command - gateway."""

from ...semantics.entity import (
    BoolOption,
    Entity,
    EntityCategory,
    EnumOptions,
    NumberRange,
)
from ...semantics.instructable import Instructable
from ...semantics.instructions.cover import (
    CoverClose,
    CoverOpen,
    CoverSetPositionAndAngle,
    CoverStop,
)
from ...semantics.instructions.dimmer import Dim, Switch
from ...semantics.observable import Observable
from ...semantics.observers.cover import cover_factory
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..message import EEPMessageType, RawEEPMessage, ValueWithContext
from ..profile import EEPDataField, EEPSpecification, EEPTelegram


def _resolve_edim(raw: dict, _scaled: dict, config: dict) -> ValueWithContext | None:
    """Convert EDIM raw value to a percentage, applying inverse brightness scaling.

    Forward (send): scaled_pct = min_b + (max_b - min_b) * dim_value / 100
    Inverse (receive): dim_value = (scaled_pct - min_b) / (max_b - min_b) * 100

    EDIMR=0 (absolute): raw 0–255 → scaled_pct 0–100 → dim_value via inverse scaling
    EDIMR=1 (relative): raw 0–100 → scaled_pct 0–100 → dim_value via inverse scaling
    """
    edim = raw.get("EDIM")
    edimr = raw.get("EDIMR")
    if edim is None or edimr is None:
        return None
    if edimr == 1:
        scaled_pct = float(edim)
    else:
        scaled_pct = edim * 100.0 / 255.0
    min_b: float = config.get("min_brightness", 0.0)
    max_b: float = config.get("max_brightness", 100.0)
    span = max_b - min_b
    if span == 0:
        dim_value = 0.0
    else:
        dim_value = (scaled_pct - min_b) / span * 100.0
    return ValueWithContext(name="Dimming value", value=round(dim_value, 1), unit="%")


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


def _encode_dim(action: Dim, config: dict) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=2, description="Dimming"),
    )
    # dim_value, min_brightness, and max_brightness are all 0–100 %.
    # Scale dim_value into [min_b, max_b] first; then encode to the wire range:
    #   Relative (EDIMR=1): wire 0–100 (already in %)
    #   Absolute (EDIMR=0): wire 0–255
    #
    # Examples with min_brightness=20, max_brightness=80:
    #   dim=  0 % → scaled= 20 % → absolute EDIM=  51,  relative EDIM= 20
    #   dim= 50 % → scaled= 50 % → absolute EDIM= 128,  relative EDIM= 50
    #   dim=100 % → scaled= 80 % → absolute EDIM= 204,  relative EDIM= 80
    #
    # Examples with defaults (min=0, max=100):
    #   dim=  0 % → scaled=  0 % → absolute EDIM=   0,  relative EDIM=  0
    #   dim= 50 % → scaled= 50 % → absolute EDIM= 128,  relative EDIM= 50
    #   dim=100 % → scaled=100 % → absolute EDIM= 255,  relative EDIM=100
    min_b: float = config.get("min_brightness", 0.0)
    max_b: float = config.get("max_brightness", 100.0)
    scaled_pct = min_b + (max_b - min_b) * action.dim_value / 100.0
    if action.use_relative:
        msg.raw["EDIM"] = max(0, min(100, round(scaled_pct)))
        msg.raw["EDIMR"] = 1
    else:
        msg.raw["EDIM"] = max(0, min(255, round(scaled_pct / 100.0 * 255)))
        msg.raw["EDIMR"] = 0
    ramp = (
        action.ramp_time
        if action.ramp_time is not None
        else int(config.get("ramp_time", 0))
    )
    msg.raw["RMP"] = max(0, min(255, ramp))
    store = (
        action.store if action.store is not None else bool(config.get("store", False))
    )
    msg.raw["STR"] = int(store)
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


def _resolve_cover_position(
    raw: dict, _scaled: dict, _config: dict
) -> ValueWithContext | None:
    """Extract position from incoming CMD=7 status (FUNC=0, PAF=1).

    P1 carries current position directly as 0–100 %.
    """
    if raw.get("FUNC") != 0 or raw.get("PAF") != 1:
        return None
    p1 = raw.get("P1")
    if p1 is None:
        return None
    return ValueWithContext(
        name="Position", value=float(max(0, min(100, p1))), unit="%"
    )


def _resolve_cover_angle(
    raw: dict, _scaled: dict, _config: dict
) -> ValueWithContext | None:
    """Extract angle from incoming CMD=7 status (FUNC=0, PAF=1).

    P2 bits[6:0] encode 0–45 representing 0–90°; scaled to 0–100 %.
    """
    if raw.get("FUNC") != 0 or raw.get("PAF") != 1:
        return None
    p2 = raw.get("P2")
    if p2 is None:
        return None
    angle_pct = round((p2 & 0x7F) * 100.0 / 45.0, 1)
    return ValueWithContext(name="Angle", value=angle_pct, unit="%")


_DIMMER_ENTITY = Entity(
    id="light",
    observables=frozenset({Observable.OUTPUT_VALUE}),
    actions=frozenset({Instructable.DIM, Instructable.SWITCH}),
)

_DIM_MODE_SELECT = Entity(
    id="dimming_mode",
    config_spec=EnumOptions(options=("relative", "absolute"), default="relative"),
    category=EntityCategory.CONFIG,
)

_MIN_BRIGHTNESS = Entity(
    id="min_brightness",
    config_spec=NumberRange(
        min_value=0.0, max_value=100.0, step=1.0, unit="%", default=0.0
    ),
    category=EntityCategory.CONFIG,
)

_MAX_BRIGHTNESS = Entity(
    id="max_brightness",
    config_spec=NumberRange(
        min_value=0.0, max_value=100.0, step=1.0, unit="%", default=100.0
    ),
    category=EntityCategory.CONFIG,
)

_RAMP_TIME = Entity(
    id="ramp_time",
    config_spec=NumberRange(
        min_value=0.0, max_value=255.0, step=1.0, unit="s", default=0.0
    ),
    category=EntityCategory.CONFIG,
)

_STORE = Entity(
    id="store",
    config_spec=BoolOption(default=False),
    category=EntityCategory.CONFIG,
)

_COVER_ENTITY = Entity(
    id="cover",
    observables=frozenset(
        {Observable.POSITION, Observable.ANGLE, Observable.COVER_STATE}
    ),
    actions=frozenset(
        {
            Instructable.COVER_STOP,
            Instructable.COVER_OPEN,
            Instructable.COVER_CLOSE,
            Instructable.COVER_SET_POSITION_AND_ANGLE,
        }
    ),
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
                    observable=Observable.POSITION,
                ),
                EEPDataField(
                    id="P2",
                    name="Parameter 2",
                    offset=16,
                    size=8,
                    range_min=0,
                    range_max=255,
                    observable=Observable.ANGLE,
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
    entities=[
        _DIMMER_ENTITY,
        _COVER_ENTITY,
        _DIM_MODE_SELECT,
        _MIN_BRIGHTNESS,
        _MAX_BRIGHTNESS,
        _RAMP_TIME,
        _STORE,
    ],
    observers=[
        scalar_factory(Observable.OUTPUT_VALUE, entity_id="light"),
        cover_factory(message_type_id=7),
    ],
    semantic_resolvers={
        Observable.OUTPUT_VALUE: _resolve_edim,
        Observable.POSITION: _resolve_cover_position,
        Observable.ANGLE: _resolve_cover_angle,
    },
    encoders={
        Instructable.SWITCH: lambda a, _: _encode_switch(a),
        Instructable.DIM: _encode_dim,
        Instructable.COVER_STOP: lambda a, _: _encode_cover_stop(a),
        Instructable.COVER_OPEN: lambda a, _: _encode_cover_open(a),
        Instructable.COVER_CLOSE: lambda a, _: _encode_cover_close(a),
        Instructable.COVER_SET_POSITION_AND_ANGLE: lambda a, _: (
            _encode_set_cover_position(a)
        ),
    },
    uses_addressed_sending=False,
)
