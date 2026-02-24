"""Window handle capability for F6-10-00 sensors."""

from dataclasses import dataclass
from time import time

from ..eep.message import EEPMessage
from .capability import Capability
from .state_change import StateChange, StateChangeSource

WINDOW_STATE_UID = "window_state"


@dataclass
class WindowStateCapability(Capability):
    """Capability that emits window handle state changes for F6-10-00 sensors."""

    def _decode_impl(self, message: EEPMessage) -> None:
        if not message.values:
            return
        if (
            message.eepid is None
            or message.eepid.rorg != 0xF6
            or message.eepid.func != 10
            or message.eepid.type != 00
        ):
            return

        win_value = message.values.get("WIN")
        if win_value is None or win_value.value is None:
            return

        self._emit(
            StateChange(
                device_address=self.device_address,
                entity_uid=WINDOW_STATE_UID,
                value=win_value.value,
                timestamp=time(),
                source=StateChangeSource.TELEGRAM,
            )
        )
