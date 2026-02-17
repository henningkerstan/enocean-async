from .id import EEPID
from .profile import EEP, EEPDataField

EEP_DATABASE: dict[EEPID, EEP] = {
    EEPID.from_string("F6-02-01"): EEP(
        id=EEPID.from_string("F6-02-01"),
        name="Light and Blind Control - Application Style 1",
        datafields=[
            EEPDataField(
                id="R1",
                name="Rocker 1st action",
                offset=0,
                size=3,
                range_min=0,
                range_max=7,
                range_enum={
                    0: "Button A1",
                    1: "Button A0",
                    2: "Button B1",
                    3: "Button B0",
                },
            ),
            EEPDataField(
                id="EB",
                name="Energy bow",
                offset=3,
                size=1,
                range_min=0,
                range_max=1,
                range_enum={0: "released", 1: "pressed"},
            ),
            EEPDataField(
                id="R2",
                name="Rocker 2nd action",
                offset=4,
                size=3,
                range_min=0,
                range_max=7,
                range_enum={
                    0: "Button A1",
                    1: "Button A0",
                    2: "Button B1",
                    3: "Button B0",
                },
            ),
            EEPDataField(
                id="SA",
                name="2nd action",
                offset=7,
                size=1,
                range_min=0,
                range_max=1,
                range_enum={0: "No 2nd action", 1: "2nd action valid"},
            ),
        ],
    ),
}
"""A simple in-memory database of supported EEP profiles. For performance reasons, this is implemented as a dictionary mapping EEPID to EEP."""
