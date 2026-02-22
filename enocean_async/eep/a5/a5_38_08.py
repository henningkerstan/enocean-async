"""A5-38-08: Central command - gateway."""

from ..id import EEPID
from ..profile import EEP, EEPDataField, EEPTelegram

EEP_A5_38_08 = EEP(
    id=EEPID.from_string("A5-38-08"),
    name="Central command - gateway",
    cmd_size=8,
    cmd_offset=0,
    telegrams={
        2: EEPTelegram(
            name="Dimming",
            datafields=[
                EEPDataField(
                    id="EDIM",
                    name="Dimming value",
                    offset=8,
                    size=8,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 255.0,
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
        )
    },
)
