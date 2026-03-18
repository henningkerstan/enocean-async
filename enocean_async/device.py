from dataclasses import dataclass, field

from .address import EURID, SenderAddress
from .eep.device_type import DeviceType
from .eep.id import EEP
from .semantics.observers.observer import Observer


@dataclass
class Device:
    """Representation of an EnOcean device."""

    address: EURID
    device_type: DeviceType
    name: str
    sender: SenderAddress | None = None
    capabilities: list[Observer] = field(default_factory=list)

    @property
    def eep(self) -> EEP:
        return self.device_type.eep
