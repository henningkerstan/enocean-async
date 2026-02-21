from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Optional

from ..eep.id import EEPID

if TYPE_CHECKING:
    from ..address import SenderAddress
    from ..capabilities.capability import Capability
    from ..capabilities.state_change import StateChange

CapabilityFactory = Callable[
    ["SenderAddress", Optional[Callable[["StateChange"], None]]], "Capability"
]


@dataclass
class DeviceType:
    """Representation of an EnOcean device type."""

    eepid: EEPID
    uid: str | None = None
    model: str | None = None
    manufacturer: str | None = None
    capability_factories: list[CapabilityFactory] = field(default_factory=list)

    def create_capabilities(
        self,
        device_address: "SenderAddress",
        on_state_change: Optional[Callable[["StateChange"], None]] = None,
    ) -> list["Capability"]:
        """Instantiate capabilities for a device instance."""
        return [
            factory(device_address, on_state_change)
            for factory in self.capability_factories
        ]
