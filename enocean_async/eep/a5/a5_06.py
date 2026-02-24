"""A5-06-XX: Light sensors."""

from ..id import EEPID
from ..manufacturer import Manufacturer
from ..profile import EEPDataField, SingleTelegramEEP


class _EEP_A5_06(SingleTelegramEEP):
    def __init__(
        self,
        _type: int,
        ill2_min: float,
        ill2_max: float,
        ill1_min: float,
        ill1_max: float,
    ):
        super().__init__(
            id=EEPID.from_string(f"A5-06-{_type:02X}"),
            name=f"Light sensor, range {min(ill1_min, ill2_min)}lx to {max(ill1_max, ill2_max)}lx",
            datafields=[
                EEPDataField(
                    id="SVC",
                    name="Supply voltage",
                    offset=0,
                    size=8,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 5.1,
                    unit_fn=lambda _: "V",
                ),
                EEPDataField(
                    id="ILL2",
                    name="Illumination",
                    offset=8,
                    size=8,
                    scale_min_fn=lambda _: ill2_min,
                    scale_max_fn=lambda _: ill2_max,
                    unit_fn=lambda _: "lx",
                ),
                EEPDataField(
                    id="ILL1",
                    name="Illumination",
                    offset=16,
                    size=8,
                    scale_min_fn=lambda _: ill1_min,
                    scale_max_fn=lambda _: ill1_max,
                    unit_fn=lambda _: "lx",
                ),
                EEPDataField(
                    id="RS",
                    name="Range select",
                    offset=31,
                    size=1,
                    range_enum={
                        0: "Use ILL1",
                        1: "Use ILL2",
                    },
                ),
            ],
        )


EEP_A5_06_01 = _EEP_A5_06(
    _type=0x01, ill2_min=300.0, ill2_max=30000.0, ill1_min=600.0, ill1_max=60000.0
)
EEP_A5_06_02 = _EEP_A5_06(
    _type=0x02, ill2_min=0.0, ill2_max=510.0, ill1_min=0.0, ill1_max=1020.0
)
EEP_A5_06_05 = _EEP_A5_06(
    _type=0x05, ill2_min=0.0, ill2_max=5100.0, ill1_min=0.0, ill1_max=10200.0
)

EEP_A5_06_03 = SingleTelegramEEP(
    id=EEPID.from_string(f"A5-06-03"),
    name=f"Light sensor, 10-bit measurement, range 0lx to 1000lx",
    datafields=[
        EEPDataField(
            id="SVC",
            name="Supply voltage",
            offset=0,
            size=8,
            range_max=250,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 5.0,
            unit_fn=lambda _: "V",
        ),
        EEPDataField(
            id="ILL",
            name="Illumination",
            offset=8,
            size=10,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 1000.0,
            unit_fn=lambda _: "lx",
        ),
    ],
)

EEP_A5_06_04 = SingleTelegramEEP(
    id=EEPID.from_string(f"A5-06-04"),
    name=f"Curtain wall brightness sensor",
    datafields=[
        EEPDataField(
            id="TEMP",
            name="Ambient temperature",
            offset=0,
            size=8,
            scale_min_fn=lambda _: -20.0,
            scale_max_fn=lambda _: 60.0,
            unit_fn=lambda _: "°C",
        ),
        EEPDataField(
            id="ILL",
            name="Illuminance",
            offset=8,
            size=16,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 65535.0,
            unit_fn=lambda _: "lx",
        ),
        EEPDataField(
            id="SV",
            name="Energy storage",
            offset=24,
            size=4,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 100.0,
            unit_fn=lambda _: "%",
        ),
        EEPDataField(
            id="TMPAV",
            name="Temperature availability",
            offset=30,
            size=1,
            range_enum={
                0: "Temperature unavailable",
                1: "Temperature available",
            },
        ),
        EEPDataField(
            id="ENAV",
            name="Energy storage availability",
            offset=31,
            size=1,
            range_enum={
                0: "Energy storage unavailable",
                1: "Energy storage available",
            },
        ),
    ],
)

EEP_A5_06_01_ELTAKO = SingleTelegramEEP(
    id=EEPID(rorg=0xA5, func=0x06, type_=0x01, manufacturer=Manufacturer.ELTAKO),
    name=f" ",
    datafields=[
        EEPDataField(
            id="ILL1",
            name="Illumination",
            offset=0,
            size=8,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 100.0,
            unit_fn=lambda _: "lx",
        ),
        EEPDataField(
            id="ILL2",
            name="Illumination",
            offset=8,
            size=8,
            scale_min_fn=lambda _: 300.0,
            scale_max_fn=lambda _: 30000.0,
            unit_fn=lambda _: "lx",
        ),
    ],
)

__all__ = [
    "EEP_A5_06_01",
    "EEP_A5_06_01_ELTAKO",
    "EEP_A5_06_02",
    "EEP_A5_06_03",
    "EEP_A5_06_04",
    "EEP_A5_06_05",
]
