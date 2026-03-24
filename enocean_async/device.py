from dataclasses import dataclass, field
from typing import Any

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
    config: dict[str, Any] = field(default_factory=dict)
    """Per-device configuration values keyed by entity ID (e.g. ``"min_brightness": 20.0``).
    Populated from EEP spec defaults at registration time; updated via ``gateway.set_device_config()``."""

    @property
    def eep(self) -> EEP:
        return self.device_type.eep
