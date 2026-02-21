from dataclasses import dataclass
from time import time

from ..eep.message import EEPMessage
from .capability import Capability
from .state_change import StateChange, StateChangeSource

POSITION_UID = "POS"
ANGLE_UID = "ANG"


@dataclass
class PositionAngleCapability(Capability):
    """Capability that emits position and angle updates for D2-05-00."""

    def _decode_impl(self, message: EEPMessage) -> None:
        if not message.values:
            return
        if message.eepid is None or message.eepid.to_string() != "D2-05-00":
            return

        if message.message_type != "Reply Position and Angle":
            print(
                f"Received unsupported message type {message.message_type} for PositionAngleCapability"
            )
            return

        pos_raw, _ = message.values.get("POS", (None, None))
        ang_raw, _ = message.values.get("ANG", (None, None))

        timestamp = time()

        if pos_raw is not None:
            self._emit(
                StateChange(
                    device_address=self.device_address,
                    entity_uid=POSITION_UID,
                    value=pos_raw,
                    timestamp=timestamp,
                    source=StateChangeSource.TELEGRAM,
                )
            )

        if ang_raw is not None:
            self._emit(
                StateChange(
                    device_address=self.device_address,
                    entity_uid=ANGLE_UID,
                    value=ang_raw,
                    timestamp=timestamp,
                    source=StateChangeSource.TELEGRAM,
                )
            )
