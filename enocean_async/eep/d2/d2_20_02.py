"""D2-20-02: Fan control, type 0x02."""

from ...semantics.instructable import Instructable
from ...semantics.instructions.fan import SetFanSpeed
from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..message import EEPMessageType, RawEEPMessage, ValueWithContext
from ..profile import EEPDataField, EEPSpecification, EEPTelegram, Entity


def _fan_speed_resolver(
    raw: dict[str, int], scaled: dict[str, ValueWithContext]
) -> ValueWithContext | None:
    """Return a numeric fan-speed value (0–100 %) from the fan status telegram.

    Special raw values 253 (Auto), 254 (Default), 255 (No change), and the
    reserved range 101–252 are ignored (return None → no Observation emitted).
    """
    fs = raw.get("FS")
    if fs is None or fs > 100:
        return None
    return ValueWithContext(name="Fan speed", value=fs, unit=None)


def _encode_set_fan_speed(action: SetFanSpeed) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=0, description="Fan control message"),
    )
    msg.raw["FS"] = action.fan_speed
    msg.raw["RSR"] = action.room_size_reference
    msg.raw["RS"] = action.room_size
    return msg


EEP_D2_20_02 = EEPSpecification(
    eep=EEP("D2-20-02"),
    name="Fan control, type 0x02",
    cmd_size=7,
    cmd_offset=1,
    telegrams={
        0: EEPTelegram(
            name="Fan control message",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=1,
                    size=7,
                    range_enum={0: "Fan control message"},
                ),
                EEPDataField(
                    id="RSR",
                    name="Room size reference",
                    offset=10,
                    size=2,
                    range_enum={
                        0: "Used",
                        1: "Not used",
                        2: "Default",
                        3: "No change",
                    },
                ),
                EEPDataField(
                    id="RS",
                    name="Room size",
                    offset=12,
                    size=4,
                    range_enum={
                        0: "< 25m²",
                        1: "25m² - 50m²",
                        2: "50m² - 75m²",
                        3: "75m² - 100m²",
                        4: "100m² - 125m²",
                        5: "125m² - 150m²",
                        6: "150m² - 175m²",
                        7: "175m² - 200m²",
                        8: "200m² - 225m²",
                        9: "225m² - 250m²",
                        10: "250m² - 275m²",
                        11: "275m² - 300m²",
                        12: "300m² - 325m²",
                        13: "325m² - 350m²",
                        14: ">350m²",
                        15: "No change",
                    },
                ),
                EEPDataField(
                    id="FS",
                    name="Fan speed",
                    offset=24,
                    size=8,
                    range_enum={
                        **{i: f"{i}%" for i in range(101)},
                        **{i: "Reserved" for i in range(101, 253)},
                        253: "Auto",
                        254: "Default",
                        255: "No change",
                    },
                ),
            ],
        ),
        1: EEPTelegram(
            name="Fan status message",
            datafields=[
                EEPDataField(
                    id="CMD",
                    name="Command",
                    offset=1,
                    size=7,
                    range_enum={1: "Fan status message"},
                ),
                EEPDataField(
                    id="HCS",
                    name="Humidity control status",
                    offset=8,
                    size=2,
                    range_enum={
                        0: "Disabled",
                        1: "Enabled",
                        2: "Reserved",
                        3: "Not supported",
                    },
                ),
                EEPDataField(
                    id="RS",
                    name="Room size",
                    offset=12,
                    size=4,
                    range_enum={
                        0: "< 25m²",
                        1: "25m² - 50m²",
                        2: "50m² - 75m²",
                        3: "75m² - 100m²",
                        4: "100m² - 125m²",
                        5: "125m² - 150m²",
                        6: "150m² - 175m²",
                        7: "175m² - 200m²",
                        8: "200m² - 225m²",
                        9: "225m² - 250m²",
                        10: "250m² - 275m²",
                        11: "275m² - 300m²",
                        12: "300m² - 325m²",
                        13: "325m² - 350m²",
                        14: ">350m²",
                        15: "No change",
                    },
                ),
                EEPDataField(
                    id="FS",
                    name="Fan speed",
                    offset=24,
                    size=8,
                    range_enum={
                        **{i: f"{i}%" for i in range(101)},
                        **{i: "Reserved" for i in range(101, 253)},
                        253: "Auto",
                        254: "Default",
                        255: "No change",
                    },
                ),
            ],
        ),
    },
    encoders={
        Instructable.SET_FAN_SPEED: lambda a, _: _encode_set_fan_speed(a),
    },
    semantic_resolvers={Observable.FAN_SPEED: _fan_speed_resolver},
    observers=[scalar_factory(Observable.FAN_SPEED, entity_id="fan")],
    entities=[
        Entity(
            id="fan",
            observables=frozenset({Observable.FAN_SPEED}),
            actions=frozenset({Instructable.SET_FAN_SPEED}),
        )
    ],
)
