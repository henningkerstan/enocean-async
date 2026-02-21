from .id import EEPID
from .profile import EEP, EEPDataField, EEPTelegram

EEP_DATABASE: dict[EEPID, EEP] = {
    EEPID.from_string("F6-02-01"): EEP(
        id=EEPID.from_string("F6-02-01"),
        name="Light and Blind Control - Application Style 1",
        cmd_size=0,
        cmd_offset=None,
        telegrams={
            0: EEPTelegram(
                name=None,
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
            )
        },
    ),
    EEPID.from_string("D2-05-00"): EEP(
        id=EEPID.from_string("D2-05-00"),
        name="Blinds Control for Position and Angle, Type 0x00",
        cmd_size=4,
        cmd_offset=-4,
        telegrams={
            4: EEPTelegram(
                name="Reply Position and Angle",
                datafields=[
                    EEPDataField(
                        id="POS",
                        name="Vertical position",
                        offset=1,
                        size=7,
                        range_min=0,
                        range_max=127,
                        unit="",
                    ),
                    EEPDataField(
                        id="ANG",
                        name="Rotation angle",
                        offset=9,
                        size=7,
                        range_min=0,
                        range_max=127,
                        unit="",
                    ),
                    EEPDataField(
                        id="LOCK",
                        name="Locking modes",
                        offset=21,
                        size=3,
                        range_min=0,
                        range_max=7,
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
                        unit="",
                    ),
                    EEPDataField(
                        id="CHN",
                        name="Channel",
                        offset=24,
                        size=4,
                        range_min=0,
                        range_max=3,
                        range_enum={
                            0: "Channel 1",
                            1: "Channel 2",
                            2: "Channel 3",
                            3: "Channel 4",
                        },
                        unit="",
                    ),
                ],
            )
        },
    ),
}
"""A simple in-memory database of supported EEP profiles. For performance reasons, this is implemented as a dictionary mapping EEPID to EEP."""
