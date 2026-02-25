"""Generic scalar capability driven by observable_uid annotation on EEP fields."""

from dataclasses import dataclass, field
from time import time

from ..eep.message import EEPMessage
from .capability import Capability
from .state_change import StateChange, StateChangeSource


@dataclass
class ScalarCapability(Capability):
    """Generic capability that emits a StateChange for any EEP field annotated with a matching observable_uid.

    This capability reads from the EEP-level observable_uid key that was propagated into EEPMessage.entities by EEPHandler.
    This makes it fully EEP-agnostic.
    """

    observable_uid: str = field(kw_only=True)
    """The entity UID to read from EEPMessage.entities and emit as a StateChange."""

    def _decode_impl(self, message: EEPMessage) -> None:
        v = message.entities.get(self.observable_uid)
        if v is None or v.value is None:
            return

        self._emit(
            StateChange(
                device_address=self.device_address,
                observable_uid=self.observable_uid,
                value=v.value,
                unit=v.unit,
                timestamp=time(),
                source=StateChangeSource.TELEGRAM,
            )
        )
