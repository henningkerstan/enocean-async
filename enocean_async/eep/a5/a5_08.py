"""A5-08-XX: Light, temperature and occupancy sensors."""

from ...capabilities.entity_uids import EntityUID
from ...capabilities.scalar_sensor import ScalarSensorCapability
from ..id import EEPID
from ..manufacturer import Manufacturer
from ..profile import EEPDataField, SingleTelegramEEP

_FULL_FACTORIES = [
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.VOLTAGE,
    ),
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.ILLUMINATION,
    ),
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.TEMPERATURE,
    ),
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.MOTION,
    ),
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.OCCUPANCY_BUTTON,
    ),
]

_ELTAKO_FACTORIES = [
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.VOLTAGE,
    ),
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.ILLUMINATION,
    ),
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.MOTION,
    ),
]


class _EEP_A5_08(SingleTelegramEEP):
    def __init__(self, _type: int, ill_max: float, temp_min: float, temp_max: float):
        super().__init__(
            id=EEPID.from_string(f"A5-08-{_type:02X}"),
            name=f"Light, temperature and occupancy sensor, range 0lx to {ill_max}lx, {temp_min}°C to {temp_max}°C and occupancy button",
            datafields=[
                EEPDataField(
                    id="SVC",
                    name="Supply voltage",
                    offset=0,
                    size=8,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 5.1,
                    unit_fn=lambda _: "V",
                    entity_uid=EntityUID.VOLTAGE,
                ),
                EEPDataField(
                    id="ILL",
                    name="Illumination",
                    offset=8,
                    size=8,
                    scale_min_fn=lambda _: 0,
                    scale_max_fn=lambda _: ill_max,
                    unit_fn=lambda _: "lx",
                    entity_uid=EntityUID.ILLUMINATION,
                ),
                EEPDataField(
                    id="TMP",
                    name="Temperature",
                    offset=16,
                    size=8,
                    scale_min_fn=lambda _: temp_min,
                    scale_max_fn=lambda _: temp_max,
                    unit_fn=lambda _: "°C",
                    entity_uid=EntityUID.TEMPERATURE,
                ),
                EEPDataField(
                    id="PIRS",
                    name="PIR status",
                    offset=30,
                    size=1,
                    range_enum={
                        0: "motion",
                        1: "no motion",
                    },
                    entity_uid=EntityUID.MOTION,
                ),
                EEPDataField(
                    id="OCC",
                    name="Occupancy button",
                    offset=31,
                    size=1,
                    range_enum={
                        0: "pressed",
                        1: "released",
                    },
                    entity_uid=EntityUID.OCCUPANCY_BUTTON,
                ),
            ],
            capability_factories=_FULL_FACTORIES,
        )


EEP_A5_08_01 = _EEP_A5_08(_type=0x01, ill_max=510, temp_min=0.0, temp_max=51.0)
EEP_A5_08_02 = _EEP_A5_08(_type=0x02, ill_max=1020, temp_min=0.0, temp_max=51.0)
EEP_A5_08_03 = _EEP_A5_08(_type=0x03, ill_max=1530, temp_min=-30.0, temp_max=50.0)

EEP_A5_08_01_ELTAKO = SingleTelegramEEP(
    id=EEPID(0xA5, 0x08, 0x01, Manufacturer.ELTAKO),
    name="Light and occupancy sensor, range 0lx to 510lx, Eltako variant (FABH65S, FBH65, FBH65TF, FBH65SB, FBH55SB, FBHF65SB, F4USM61B)",
    datafields=[
        EEPDataField(
            id="SVC",
            name="Supply voltage",
            offset=0,
            size=8,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 5.1,
            unit_fn=lambda _: "V",
            entity_uid=EntityUID.VOLTAGE,
        ),
        EEPDataField(
            id="ILL",
            name="Illumination",
            offset=8,
            size=8,
            scale_min_fn=lambda _: 0,
            scale_max_fn=lambda _: 510,
            unit_fn=lambda _: "lx",
            entity_uid=EntityUID.ILLUMINATION,
        ),
        EEPDataField(
            id="PIRS",
            name="PIR status",
            offset=24,
            size=8,
            range_enum={
                0x0D: "motion",
                0x0F: "no motion",
            },
            entity_uid=EntityUID.MOTION,
        ),
    ],
    capability_factories=_ELTAKO_FACTORIES,
)
