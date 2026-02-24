from dataclasses import dataclass
from time import time

from ..eep.manufacturer import Manufacturer
from ..eep.message import EEPMessage
from .capability import Capability
from .state_change import StateChange, StateChangeSource

ILLUMINATION_UID = "illumination"


@dataclass
class IlluminationSensorCapability(Capability):
    """Capability that emits illumination updates for A5-07-03 and A5-06-xx sensors."""

    def _decode_impl(self, message: EEPMessage) -> None:
        if not message.values:
            return
        if message.eepid is None:
            return

        eepid = message.eepid
        if eepid.to_string() == "A5-07-03":
            ill_value = message.values.get("ILL")
        elif eepid.rorg == 0xA5 and eepid.func == 0x06:
            ill_value = self._select_a5_06_illumination(message)
        else:
            return

        if ill_value is None or ill_value.value is None:
            return

        self._emit(
            StateChange(
                device_address=self.device_address,
                entity_uid=ILLUMINATION_UID,
                value=ill_value.value,
                timestamp=time(),
                source=StateChangeSource.TELEGRAM,
            )
        )

    def _select_a5_06_illumination(self, message: EEPMessage):
        """Select the illumination value for A5-06 variants."""
        ill_value = message.values.get("ILL")
        if ill_value is not None:
            return ill_value

        ill1_value = message.values.get("ILL1")
        ill2_value = message.values.get("ILL2")
        rs_value = message.values.get("RS")

        if message.eepid and message.eepid.manufacturer == Manufacturer.ELTAKO:
            if ill2_value is not None and ill2_value.raw == 0:
                return ill1_value
            return ill2_value or ill1_value

        if rs_value is not None:
            if rs_value.raw == 0:
                return ill1_value
            if rs_value.raw == 1:
                return ill2_value

        return ill2_value or ill1_value
