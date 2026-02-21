from dataclasses import dataclass

from ..address import EURID, SenderAddress
from .type import DeviceType


@dataclass
class Device:
    """Representation of an EnOcean device."""

    id: EURID
    type: DeviceType
    name: str
    sender: SenderAddress | None = None
    telegrams_received: int = 0
