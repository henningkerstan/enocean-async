"""Device catalog: human-readable manufacturer/model → EEPID lookup.

This catalog contains well-known device models with non-standard EEP assignments
(e.g. manufacturer-specific variants). Generic EEP profiles are available directly
via EEP_DATABASE without needing a catalog entry.
"""

from dataclasses import dataclass

from ..eep.id import EEPID
from ..eep.manufacturer import Manufacturer


@dataclass
class DeviceCatalogEntry:
    """A known device model with its associated EEPID."""

    eepid: EEPID
    manufacturer: str
    model: str
    uid: str | None = None


DEVICE_CATALOG: list[DeviceCatalogEntry] = [
    DeviceCatalogEntry(
        eepid=EEPID(0xA5, 0x08, 0x01, manufacturer=Manufacturer.ELTAKO),
        manufacturer="Eltako",
        model="FABH65S Wireless outdoor occupancy and brightness sensor",
        uid="Eltako_FABH65S",
    ),
    DeviceCatalogEntry(
        eepid=EEPID(0xD2, 0x05, 0x00),
        manufacturer="NodOn",
        model="SIN-2-RS-01 Roller Shutter Controller",
        uid="NodOn_SIN-2-RS-01",
    ),
]
