from dataclasses import dataclass, field

from ..address import EURID, SenderAddress
from ..capabilities.capability import Capability
from ..eep.id import EEPID


@dataclass
class Device:
    """Representation of an EnOcean device."""

    address: EURID
    eepid: EEPID
    name: str
    sender: SenderAddress | None = None
    telegrams_received: int = 0
    capabilities: list[Capability] = field(default_factory=list)
