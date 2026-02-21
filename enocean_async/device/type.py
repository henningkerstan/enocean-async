from dataclasses import dataclass

from ..eep.id import EEPID


@dataclass
class DeviceType:
    """Representation of an EnOcean device type."""

    eepid: EEPID
    uid: str | None = None
    model: str | None = None
    manufacturer: str | None = None

    def is_generic(self) -> bool:
        """Check if the device type is generic (i.e., has no specific model or manufacturer information)."""
        return self.uid is not None and self.uid == self.eepid.to_string()
