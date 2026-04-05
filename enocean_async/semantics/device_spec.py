from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..eep.id import EEP
from .entity import Entity

if TYPE_CHECKING:
    from ..eep.device_type import DeviceType


@dataclass
class DeviceSpec:
    """Setup-time description of what a device type exposes and accepts.

    Built by ``gateway.device_spec(address)``.  An integration can obtain
    this immediately after calling ``gateway.add_device()`` — before any telegrams arrive
    — and use it to create all required platform entities.
    """

    device_type: "DeviceType"
    """The device type (manufacturer + model + EEP) this spec was built for."""

    entities: list[Entity]
    """All entities this device type exposes, including the metadata entities
    (rssi, last_seen, telegram_count) and the sender_slot config entity,
    always added by the gateway.
    """

    gateway_entities: list[Entity] = field(default_factory=list)
    """Entities sourced from the gateway device but useful for configuration of this device. """

    @property
    def eep(self) -> EEP:
        """The EEP of this device type. Shortcut for ``device_type.eep``."""
        return self.device_type.eep
