"""D2-20-02: Fan control, type 0x02."""

from ...capabilities.action_uid import ActionUID
from ...capabilities.fan_actions import SetFanSpeedAction
from ..id import EEP
from ..message import EEPMessage, EEPMessageType, EEPMessageValue
from ..profile import EEPDataField, EEPSpecification, EEPTelegram

EEP_D2_01_TelegramNames = {
    1: "Actuator set output",
}


EEP_D2_01_Telegrams = {
    1: EEPTelegram(
        name="Actuator set output",
        datafields=[
            EEPDataField(
                id="CMD",
                name="Command",
                offset=4,
                size=4,
                range_enum={1: "Actuator set output"},
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
    telegrams={EEP_D2_01_Telegrams[1]},
    command_encoders=None,
)
