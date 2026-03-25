from .manufacturer import Manufacturer


class EEP:
    """Identifier of an EnOcean Equipment Profile (EEP), e.g. F6-02-01 or D2-05-00.

    Construct from a dash-separated hex string or a 3-element int list:

        EEP("A5-08-01")
        EEP("A5-08-01", Manufacturer.ELTAKO)
        EEP("A5-08-01.ELTAKO")          # manufacturer embedded in string
        EEP([0xA5, 0x08, 0x01])
        EEP([0xA5, func, type_], mfr)   # used internally when parsing telegrams
    """

    def __init__(
        self, eep: str | list[int], manufacturer: Manufacturer | None = None
    ) -> None:
        if isinstance(eep, str):
            eep_part, _, manufacturer_part = eep.strip().partition(".")
            parts = eep_part.split("-")
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid EEP string '{eep}': expected 'XX-XX-XX' or 'XX-XX-XX.MANUFACTURER'."
                )
            self.rorg = int(parts[0], 16)
            self.func = int(parts[1], 16)
            self.type = int(parts[2], 16)
            if manufacturer_part:
                try:
                    embedded = Manufacturer[manufacturer_part.upper()]
                except KeyError:
                    raise ValueError(f"Unknown manufacturer: '{manufacturer_part}'.")
                if manufacturer is not None and manufacturer != embedded:
                    raise ValueError(
                        f"Conflicting manufacturers: string has '{embedded.name}' but kwarg has '{manufacturer.name}'."
                    )
                self.manufacturer = embedded
            else:
                self.manufacturer = manufacturer
        elif isinstance(eep, list):
            if len(eep) != 3:
                raise ValueError(
                    f"List form requires exactly 3 elements [rorg, func, type_], got {len(eep)}."
                )
            self.rorg = eep[0]
            self.func = eep[1]
            self.type = eep[2]
            self.manufacturer = manufacturer
        else:
            raise TypeError(
                "EEP requires a dash-separated string ('A5-08-01') or a 3-element int list ([0xA5, 0x08, 0x01])."
            )

    def __str__(self) -> str:
        """Dash-separated hex string, e.g. ``'A5-08-01'`` or ``'A5-08-01.ELTAKO'``."""
        base = f"{self.rorg:02X}-{self.func:02X}-{self.type:02X}"
        return base if self.manufacturer is None else f"{base}.{self.manufacturer.name}"

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash((self.rorg, self.func, self.type, self.manufacturer))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EEP):
            return NotImplemented
        return (
            self.rorg == other.rorg
            and self.func == other.func
            and self.type == other.type
            and self.manufacturer == other.manufacturer
        )
