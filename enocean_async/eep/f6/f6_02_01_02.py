"""F6-02: Rocker Switch, 2 Rocker - Application Styles 1 & 2.

This module contains F6-02-01 and F6-02-02 profiles, which share identical
telegram structures and only differ in their application-level interpretation.

Profiles in this module:
- F6-02-01: Light and blind control - application style 1
- F6-02-02: Light and blind control - application style 2
"""

from ..id import EEPID
from ..profile import EEPDataField, SingleTelegramEEP

# Shared datafields definition for all F6-02-xx profiles
_F6_02_DATAFIELDS = [
    EEPDataField(
        id="R1",
        name="Rocker 1st action",
        offset=0,
        size=3,
        range_min=0,
        range_max=7,
        range_enum={
            0: "a1",
            1: "a0",
            2: "b1",
            3: "b0",
        },
    ),
    EEPDataField(
        id="EB",
        name="Energy bow",
        offset=3,
        size=1,
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
            0: "a1",
            1: "a0",
            2: "b1",
            3: "b0",
        },
    ),
    EEPDataField(
        id="SA",
        name="2nd action",
        offset=7,
        size=1,
        range_enum={0: "No 2nd action", 1: "2nd action valid"},
    ),
]


# Define all F6-02-xx variants using the shared datafields structure
EEP_F6_02_01 = SingleTelegramEEP(
    id=EEPID.from_string("F6-02-01"),
    name="Light and blind control - application style 1",
    datafields=_F6_02_DATAFIELDS,
)

EEP_F6_02_02 = SingleTelegramEEP(
    id=EEPID.from_string("F6-02-02"),
    name="Light and blind control - application style 2",
    datafields=_F6_02_DATAFIELDS,
)
