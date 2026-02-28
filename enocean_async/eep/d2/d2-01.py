"""D2-20-02: Fan control, type 0x02."""

from dataclasses import dataclass

from ...capabilities.action_uid import ActionUID
from ...capabilities.fan_actions import SetFanSpeedAction
from ..id import EEP
from ..message import EEPMessage, EEPMessageType, EEPMessageValue
from ..profile import EEPDataField, EEPSpecification, EEPTelegram


@dataclass(frozen=True)
class EEP_D2_01_TelegramName:
    key: int
    name: str


EEP_D2_01_Commands = {
    0x1: EEP_D2_01_TelegramName(key=0x1, name="Actuator set output"),
    0x2: EEP_D2_01_TelegramName(key=0x2, name="Actuator set local"),
    0x3: EEP_D2_01_TelegramName(key=0x3, name="Actuator status query"),
    0x4: EEP_D2_01_TelegramName(key=0x4, name="Actuator status response"),
    0x5: EEP_D2_01_TelegramName(key=0x5, name="Actuator set measurement"),
    0x6: EEP_D2_01_TelegramName(key=0x6, name="Actuator measurement query"),
    0x7: EEP_D2_01_TelegramName(key=0x7, name="Actuator measurement response"),
    0x8: EEP_D2_01_TelegramName(key=0x8, name="Actuator set pilot wire mode"),
    0x9: EEP_D2_01_TelegramName(key=0x9, name="Actuator pilot wire mode query"),
    0xA: EEP_D2_01_TelegramName(key=0xA, name="Actuator pilot wire mode response"),
    0xB: EEP_D2_01_TelegramName(
        key=0xB, name="Actuator set external interface settings"
    ),
    0xC: EEP_D2_01_TelegramName(
        key=0xC, name="Actuator external interface settings query"
    ),
    0xD: EEP_D2_01_TelegramName(
        key=0xD, name="Actuator external interface settings response"
    ),
    0xF: EEP_D2_01_TelegramName(key=0xF, name="Extended command, see ECID field"),
}

EEP_D2_01_ExtendedCommands = {
    EEP_D2_01_TelegramName(
        key=0x00, name="Actuator dimming limits query"
    ): "Actuator dimming limits query",
    EEP_D2_01_TelegramName(
        key=0x01, name="Actuator dimming limits response"
    ): "Actuator dimming limits response",
}

EEP_D2_01_Telegrams = {
    1: EEPTelegram(
        name=EEP_D2_01_Commands[1].name,
        datafields=[
            EEPDataField(
                id="CMD",
                name="Command",
                offset=4,
                size=4,
                range_enum={
                    **{
                        telegram.key: telegram.name
                        for telegram in EEP_D2_01_Commands.values()
                    }
                },
            ),
            EEPDataField(
                id="DV",
                name="Dim value",
                offset=8,
                size=3,
                range_enum={
                    0x00: "Switch to new output value",
                    0x01: "Dim to new output value - dim timer 1",
                    0x02: "Dim to new output value - dim timer 2",
                    0x03: "Dim to new output value - dim timer 3",
                    0x04: "Stop Dimming",
                    0x05: "Not used",
                    0x06: "Not used",
                    0x07: "Not used",
                },
            ),
            EEPDataField(
                id="IO",
                name="Input/output channel",
                offset=11,
                size=5,
                range_enum={
                    **{0x00 + i: f"Input channel {i + 1}" for i in range(30)},
                    0x1E: "All channels",
                    0x1F: "Input channel",
                },
            ),
            EEPDataField(
                id="OV",
                name="Output value",
                offset=17,
                size=7,
                range_enum={
                    0x00: "0% or OFF",
                    **{i: f"{i}% or ON" for i in range(1, 0x65)},
                    **{i: "Not used" for i in range(0x65, 0x7F)},
                    0x7F: "Output value not valid or not applicable",
                },
            ),
        ],
    )
}

EEP_D2_01_00 = EEPSpecification(
    eep=EEP.from_string("D2-01-00"),
    name="Electronic switches and dimmers with local control, type 0x00",
    cmd_size=4,
    cmd_offset=4,
    ecid_offset=8,
    ecid_size=8,
    telegrams={EEP_D2_01_Telegrams[1]},
    command_encoders=None,
)
