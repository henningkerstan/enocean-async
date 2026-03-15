from dataclasses import dataclass

from ..eep.id import EEP
from .entity import Entity


@dataclass
class DeviceSpec:
    """Setup-time description of what a device type exposes and accepts.

    Returned by ``EEPSpecification.device_spec()``.  An integration can obtain
    this immediately after calling ``gateway.add_device()`` — before any telegrams arrive
    — and use it to create all required platform entities.
    """

    eep: EEP

    entities: list[Entity]
    """All entities this device type exposes, including the three metadata entities
    (rssi, last_seen, telegram_count) always added by the gateway.
    """
