from .manufacturer import Manufacturer


class EEP:
    """Identifier of an EnOcean Equipment Profile (EEP), e.g. F6-02-01 or D2-05-00.

    Construct from a dash-separated hex string or a 3-element int list:

        EEP("A5-08-01")
        EEP("A5-08-01", Manufacturer.ELTAKO)
        EEP("A5-08-01.ELTAKO")               # manufacturer embedded in string
        EEP("A5-7F-3F.ELTAKO.FSB")           # manufacturer + variant embedded
        EEP([0xA5, 0x08, 0x01])
        EEP([0xA5, func, type_], mfr)         # used internally when parsing telegrams
        EEP([0xA5, 0x7F, 0x3F], Manufacturer.ELTAKO, variant="FSB")

    The ``variant`` field disambiguates manufacturer-specific EEPs where the same
    three EEP bytes are reused for physically different devices with incompatible
    payload layouts (e.g. Eltako A5-7F-3F is used by both the FSB roller-shutter
    family and the FRGBW colour dimmer).  Like ``manufacturer``, ``variant`` is a
    registration-time discriminator — it is never carried on the wire.
    """

    def __init__(
        self,
        eep: str | list[int],
        manufacturer: Manufacturer | None = None,
        *,
        variant: str | None = None,
    ) -> None:
        if isinstance(eep, str):
            # Split "XX-XX-XX[.MANUFACTURER[.VARIANT]]"
            eep_part, _, rest = eep.strip().partition(".")
            parts = eep_part.split("-")
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid EEP string '{eep}': expected 'XX-XX-XX' or 'XX-XX-XX.MANUFACTURER[.VARIANT]'."
                )
            self.rorg = int(parts[0], 16)
            self.func = int(parts[1], 16)
            self.type = int(parts[2], 16)

            manufacturer_part, _, variant_part = rest.partition(".")

            if manufacturer_part:
                try:
                    embedded_mfr = Manufacturer[manufacturer_part.upper()]
                except KeyError:
                    raise ValueError(f"Unknown manufacturer: '{manufacturer_part}'.")
                if manufacturer is not None and manufacturer != embedded_mfr:
                    raise ValueError(
                        f"Conflicting manufacturers: string has '{embedded_mfr.name}' but kwarg has '{manufacturer.name}'."
                    )
                self.manufacturer = embedded_mfr
            else:
                self.manufacturer = manufacturer

            embedded_variant = variant_part.upper() if variant_part else None
            if (
                embedded_variant
                and variant is not None
                and variant.upper() != embedded_variant
            ):
                raise ValueError(
                    f"Conflicting variants: string has '{embedded_variant}' but kwarg has '{variant}'."
                )
            self.variant: str | None = embedded_variant or (
                variant.upper() if variant else None
            )

        elif isinstance(eep, list):
            if len(eep) != 3:
                raise ValueError(
                    f"List form requires exactly 3 elements [rorg, func, type_], got {len(eep)}."
                )
            self.rorg = eep[0]
            self.func = eep[1]
            self.type = eep[2]
            self.manufacturer = manufacturer
            self.variant = variant.upper() if variant else None
        else:
            raise TypeError(
                "EEP requires a dash-separated string ('A5-08-01') or a 3-element int list ([0xA5, 0x08, 0x01])."
            )

    def __str__(self) -> str:
        """Dash-separated hex string, e.g. ``'A5-08-01'``, ``'A5-08-01.ELTAKO'``, or ``'A5-7F-3F.ELTAKO.FSB'``."""
        base = f"{self.rorg:02X}-{self.func:02X}-{self.type:02X}"
        if self.manufacturer is not None:
            base = f"{base}.{self.manufacturer.name}"
        if self.variant is not None:
            base = f"{base}.{self.variant}"
        return base

    def __repr__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return hash((self.rorg, self.func, self.type, self.manufacturer, self.variant))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EEP):
            return NotImplemented
        return (
            self.rorg == other.rorg
            and self.func == other.func
            and self.type == other.type
            and self.manufacturer == other.manufacturer
            and self.variant == other.variant
        )
