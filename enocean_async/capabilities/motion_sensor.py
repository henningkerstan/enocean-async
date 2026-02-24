from dataclasses import dataclass
from time import time

from ..eep.message import EEPMessage
from .capability import Capability
from .state_change import StateChange, StateChangeSource

MOTION_UID = "motion"


@dataclass
class MotionSensorCapability(Capability):
    """Capability that emits motion/occupancy updates for A5-07-03 and A5-08 sensors."""

    def _decode_impl(self, message: EEPMessage) -> None:
        if not message.values:
            return
        if message.eepid is None:
            return

        eepid = message.eepid
        if eepid.to_string() == "A5-07-03":
            pir_value = message.values.get("PIR")
        elif eepid.rorg == 0xA5 and eepid.func == 0x08:
            pir_value = message.values.get("PIRS")
        else:
            return

        if pir_value is None or pir_value.value is None:
            return

        self._emit(
            StateChange(
                device_address=self.device_address,
                entity_uid=MOTION_UID,
                value=pir_value.value,
                timestamp=time(),
                source=StateChangeSource.TELEGRAM,
            )
        )
