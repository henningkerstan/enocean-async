"""Generic scalar sensor capability driven by entity_uid annotation on EEP fields."""

from dataclasses import dataclass, field
from time import time

from ..eep.message import EEPMessage
from .capability import Capability
from .state_change import StateChange, StateChangeSource


@dataclass
class ScalarSensorCapability(Capability):
    """Generic capability that emits a StateChange for any EEP field annotated with a matching entity_uid.

    Instead of hard-coding EEP IDs and field names, this capability reads from the
    EEP-level entity_uid key that was propagated into EEPMessage.values by EEPHandler.
    This makes it fully EEP-agnostic.
    """

    entity_uid: str = field(kw_only=True)
    """The entity UID to read from EEPMessage.values and emit as a StateChange."""

    def _decode_impl(self, message: EEPMessage) -> None:
        v = message.values.get(self.entity_uid)
        if v is None or v.value is None:
            return

        self._emit(
            StateChange(
                device_address=self.device_address,
                entity_uid=self.entity_uid,
                value=v.value,
                unit=v.unit,
                timestamp=time(),
                source=StateChangeSource.TELEGRAM,
            )
        )
