from dataclasses import dataclass, field
from typing import Callable, Optional

from ..address import EURID, SenderAddress
from ..capabilities.capability import Capability
from ..capabilities.state_change import StateChange
from .type import DeviceType


@dataclass
class Device:
    """Representation of an EnOcean device."""

    id: EURID
    type: DeviceType
    name: str
    sender: SenderAddress | None = None
    telegrams_received: int = 0
    capabilities: list[Capability] = field(default_factory=list)

    def init_capabilities(
        self, on_state_change: Optional[Callable[[StateChange], None]] = None
    ) -> None:
        """Instantiate capabilities based on the device type."""
        self.capabilities = self.type.create_capabilities(self.id, on_state_change)
