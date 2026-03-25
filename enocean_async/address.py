type SenderAddress = EURID | BaseAddress
"""Addresses that can be used as the sender of a telegram. This includes both EURIDs (device addresses) and Base IDs, hence ranges from 00:00:00:00 to FF:FF:FF:FE."""


class Address:
    """EnOcean four byte (32 bit) address to identify devices, usually denoted as a colon-separated string (e.g., 00:00:00:00)."""

    def __init__(self, value: int | str | bytes | bytearray | list[int]) -> None:
        """Create an address from an integer, a colon-separated hex string (e.g. ``"AB:CD:EF:01"``), or a 4-byte sequence."""
        if isinstance(value, (bytes, bytearray, list)):
            if len(value) != 4:
                raise ValueError("Byte sequence must have exactly 4 elements.")
            value = int.from_bytes(value, "big")
        elif isinstance(value, str):
            parts = value.strip().split(":")
            if len(parts) != 4:
                raise ValueError(
                    f"Invalid address string '{value}': expected 4 colon-separated hex bytes."
                )
            value = int("".join(part.zfill(2) for part in parts), 16)
        elif not isinstance(value, int):
            raise TypeError(
                "Address must be an integer, a colon-separated hex string, or a 4-byte sequence."
            )
        if not (0 <= value <= 0xFFFFFFFF):
            raise ValueError(
                f"Address out of range: must be between 0x00000000 and 0xFFFFFFFF, got {value}."
            )
        self._address = value

    def is_eurid(self) -> bool:
        """Return ``True`` if this address is in the EURID range (00:00:00:00–FF:7F:FF:FF)."""
        return 0x00000000 <= self._address <= 0xFF7FFFFF

    def is_base_address(self) -> bool:
        """Return ``True`` if this address is in the base address range (FF:80:00:00–FF:FF:FF:FE)."""
        return 0xFF800000 <= self._address <= 0xFFFFFFFE

    def is_broadcast(self) -> bool:
        """Return ``True`` if this is the broadcast address (FF:FF:FF:FF)."""
        return self._address == 0xFFFFFFFF

    @property
    def bytelist(self) -> list[int]:
        """Return the address as a list of 4 big-endian bytes."""
        return [
            (self._address >> 24) & 0xFF,
            (self._address >> 16) & 0xFF,
            (self._address >> 8) & 0xFF,
            self._address & 0xFF,
        ]

    def __int__(self) -> int:
        """Return the address as a 32-bit integer."""
        return self._address

    def __str__(self) -> str:
        """Return the address as a colon-separated uppercase hex string (e.g. ``"AB:CD:EF:01"``)."""
        s = f"{self._address:08X}"
        return f"{s[0:2]}:{s[2:4]}:{s[4:6]}:{s[6:8]}"

    def __hash__(self) -> int:
        """Return a hash based on the integer value of the address, so addresses are usable as dict keys."""
        return self._address

    def __eq__(self, other: object) -> bool:
        """Compare by integer value, regardless of subclass."""
        return int(self) == int(other)

    def __repr__(self) -> str:
        """Colon-separated hex string representation (e.g. ``"AB:CD:EF:01"``)."""
        return str(self)


class EURID(Address):
    """Representation of an EnOcean device address (EnOcean Unique Radio Identifier / EURID) - range ``00:00:00:00`` to ``FF:7F:FF:FF``."""

    def __init__(self, value: int | str | bytes | bytearray | list[int]) -> None:
        """Create a EURID; raises ``ValueError`` if the value is outside the EURID range."""
        super().__init__(value)
        if not (0x00000000 <= self._address <= 0xFF7FFFFF):
            raise ValueError(
                f"Device address must be in the range 00:00:00:00 to FF:7F:FF:FF, but is {self._address:08X}."
            )


class BaseAddress(Address):
    """Representation of an EnOcean base address - range ``FF:80:00:00`` to ``FF:FF:FF:FE``."""

    def __init__(self, value: int | str | bytes | bytearray | list[int]) -> None:
        """Create a BaseAddress; raises ``ValueError`` if the value is outside the base address range."""
        super().__init__(value)
        if not (0xFF800000 <= self._address <= 0xFFFFFFFE):
            raise ValueError(
                "Base address must be in the range FF:80:00:00 to FF:FF:FF:FE."
            )


class BroadcastAddress(Address):
    """Representation of the EnOcean broadcast address (FF:FF:FF:FF)."""

    def __init__(self) -> None:
        """Create the broadcast address (FF:FF:FF:FF)."""
        super().__init__(0xFFFFFFFF)
