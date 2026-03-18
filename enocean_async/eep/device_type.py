"""Device-type catalog: known physical devices mapped to EEPs.

Each :class:`DeviceType` entry associates a manufacturer and model name with its
EnOcean Equipment Profile.  Entries with ``manufacturer=None`` are generic
EEP-level entries derived directly from :data:`EEP_SPECIFICATIONS`; they are
included automatically so that the catalog always stays in sync with supported
profiles.  Manufacturer-specific entries represent known physical products and
are listed after the generic ones in lookup results.

The catalog is intended to be used by integrations (e.g. Home Assistant) to let users choose
their device by name rather than entering an EEP code directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from . import EEP_SPECIFICATIONS
from .id import EEP
from .manufacturer import Manufacturer


@dataclass(frozen=True)
class DeviceType:
    """A known physical device or generic EEP category.

    ``manufacturer=None`` marks a generic entry (any manufacturer implementing
    this EEP).  Manufacturer-specific entries narrow the selection to a single
    known product and are intended for UI/UX.
    """

    manufacturer: Manufacturer | None
    model: str
    eep: EEP
    description: str = ""

    @property
    def identifier(self) -> str:
        """Stable string identifier for this device type.

        Always ``{NAMESPACE}/{CODE}`` in uppercase:

        - Generic entries use ``EEP`` as the namespace: ``"EEP/A5-02-01"``.
        - Manufacturer-specific entries use the manufacturer enum name: ``"ELTAKO/FAH65S"``,
          ``"TRIO_2_SYS/WALL-SWITCH"``.
        """
        if self.manufacturer is not None:
            return f"{self.manufacturer.name}/{self.model.replace(' ', '-')}".upper()
        if self.eep.manufacturer is not None:
            eep_code = f"{self.eep.rorg:02X}-{self.eep.func:02X}-{self.eep.type:02X}"
            return f"{self.eep.manufacturer.name}/{eep_code}"
        return f"EEP/{self.eep}"


# ---------------------------------------------------------------------------
# Manufacturer-specific entries
# Generic EEP entries are generated automatically from EEP_SPECIFICATIONS
# (see _build_device_types() below) — do not duplicate them here.
# ---------------------------------------------------------------------------

_Eltako = partial(DeviceType, Manufacturer.ELTAKO)
_NodOn = partial(DeviceType, Manufacturer.NODON)

_MANUFACTURER_TYPES: list[DeviceType] = [
    # Eltako
    _Eltako(
        "FAH65S",
        EEP("A5-06-01", Manufacturer.ELTAKO),
        "Wireless outdoor brightness sensor",
    ),
    _Eltako(
        "FABH65S",
        EEP("A5-08-01", Manufacturer.ELTAKO),
        "Wireless outdoor occupancy and brightness sensor",
    ),
    _Eltako("FUD61NPN", EEP("A5-38-08"), "Wireless universal dimmer 230V"),
    _Eltako("FLD61", EEP("A5-38-08"), "PWM LED dimmer 12–36 V DC, up to 4 A"),
    _Eltako("FT55", EEP("F6-02-01"), "Battery-less wireless wall switch"),
    # Hoppe
    DeviceType(
        Manufacturer.HOPPE, "SecuSignal", EEP("F6-10-00"), "Wireless window handle"
    ),
    # Jung
    DeviceType(Manufacturer.JUNG, "ENO", EEP("F6-02-01"), "Wireless wall switch"),
    # NodOn
    _NodOn("PIR-2-1-01", EEP("A5-07-03"), "Motion sensor"),
    _NodOn("SIN-2-1-01", EEP("D2-01-0F"), "Single channel relay switch"),
    _NodOn("SIN-2-2-01", EEP("D2-01-12"), "Dual channel relay switch"),
    _NodOn("SIN-2-RS-01", EEP("D2-05-00"), "Roller shutter controller"),
    # Omnio
    DeviceType(
        Manufacturer.OMNIO, "WS-CH-102", EEP("F6-02-01"), "Wireless wall switch"
    ),
    # Permundo
    DeviceType(
        Manufacturer.PERMUNDO,
        "PSC234",
        EEP("D2-01-09"),
        "Wireless switch with power monitor",
    ),
    # Trio 2 Sys
    DeviceType(
        Manufacturer.TRIO_2_SYS, "Wall Switch", EEP("F6-02-01"), "Wireless wall switch"
    ),
]


def _build_device_types() -> list[DeviceType]:
    """Combine generic EEP entries (from EEP_SPECIFICATIONS) with manufacturer-specific ones."""
    generic = [
        DeviceType(None, spec.name, spec.eep) for spec in EEP_SPECIFICATIONS.values()
    ]
    return generic + _MANUFACTURER_TYPES


DEVICE_TYPES: list[DeviceType] = _build_device_types()
