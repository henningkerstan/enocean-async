from dataclasses import dataclass

from .manufacturer import Manufacturer


@dataclass
class EEP:
    """Identifier of an EnOcean Equipment Profile (EEP), e.g. F6-02-01 or D2-05-00."""

    def __init__(
        self, rorg: int, func: int, type_: int, manufacturer: Manufacturer | None = None
    ) -> None:
        """Construct an EnOcean Equipment Profile."""
        self.rorg = rorg
        self.func = func
        self.type = type_
        self.manufacturer = manufacturer  # see https://www.enocean.com/wp-content/uploads/application-notes/new_AN514_EnOcean_Link_Profiles.pdf

    @classmethod
    def from_string(cls, eep_string: str) -> "EEP":
        """Create an EEP instance from a dash-separated string, optionally with manufacturer suffix.

        Examples:
            "A5-08-01" -> EEP(0xA5, 0x08, 0x01)
            "A5-08-01.ELTAKO" -> EEP(0xA5, 0x08, 0x01, Manufacturer.ELTAKO)
        """
        # Split manufacturer suffix if present
        eep_part, _, manufacturer_part = eep_string.strip().partition(".")

        parts = eep_part.split("-")
        if len(parts) != 3:
            raise ValueError(
                "Wrong format. Expected 'XX-XX-XX' or 'XX-XX-XX.MANUFACTURER'"
            )
        rorg = int(parts[0], 16)
        func = int(parts[1], 16)
        type_ = int(parts[2], 16)

        manufacturer = None
        if manufacturer_part:
            # Try to look up manufacturer by name
            try:
                manufacturer = Manufacturer[manufacturer_part.upper()]
            except KeyError:
                raise ValueError(f"Unknown manufacturer: {manufacturer_part}")

        return cls(rorg, func, type_, manufacturer)

    def __str__(self) -> str:
        """Return the EEP as a dash-separated string, optionally with manufacturer suffix."""
        return f"{self.rorg:02X}-{self.func:02X}-{self.type:02X}{'.' + self.manufacturer.name if self.manufacturer is not None else ''}"

    def __repr__(self) -> str:
        return f"EEP({str(self)})"

    def __hash__(self):
        return hash((self.rorg, self.func, self.type, self.manufacturer))
