from dataclasses import dataclass
from time import time

from ..eep.message import EEPMessage
from .capability import Capability
from .state_change import StateChange, StateChangeSource

TEMPERATURE_UID = "temperature"


@dataclass
class TemperatureSensorCapability(Capability):
    """Capability that emits temperature updates for A5-02-XX and A5-08 sensors."""

    def _decode_impl(self, message: EEPMessage) -> None:
        if not message.values:
            return
        if message.eepid is None:
            return

        eepid = message.eepid
        if eepid.rorg != 0xA5 or eepid.func not in (0x02, 0x08):
            return

        temp_value = message.values.get("TMP")
        if temp_value is None or temp_value.value is None:
            return

        self._emit(
            StateChange(
                device_address=self.device_address,
                entity_uid=TEMPERATURE_UID,
                value=temp_value.value,
                timestamp=time(),
                source=StateChangeSource.TELEGRAM,
            )
        )
