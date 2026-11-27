"""Security Level Format (SLF): the byte that describes how a device secures its telegrams.

Reference: *Security of EnOcean Radio Networks* V4.03, §4.6 (current encoding, Table 3) and
Annex C (legacy encoding). Both encodings share the bit layout:

    bits 7–5  RLC size (internal and transmitted)
    bits 4–3  MAC size
    bits 2–0  security mode (current: bit 2 RFU, bits 1–0 the mode; legacy: encryption type)

The legacy VAES encoding (0b011) equals the current VAES encoding (bit 2 = 0, mode 0b11), so
VAES values are read the same way in both. CCM (mode 0b01) exists in the current encoding only.
"""

from dataclasses import dataclass
from enum import Enum


class SecurityMode(Enum):
    """Algorithm used to encrypt and authenticate a telegram (§4.1, §4.6.1)."""

    VAES_CMAC = "VAES with CMAC"
    """VAES encryption (§7.1) with a CMAC (§7.2, RFC 4493); the legacy mode."""

    CCM = "CCM"
    """Counter with CBC-MAC (§7.3, RFC 3610); the mode for new designs."""


_MODE_VAES = 0b011  # bits 2–0; legacy ENCRYPTION_TYPE VAES = current RFU 0 + mode 0b11
_MODE_CCM = 0b001  # bits 2–0; current only: RFU 0 + mode 0b01

# MAC size field (bits 4–3) → MAC size in bytes
_MAC_SIZES = {0b01: 3, 0b10: 4}

# RLC size field (bits 7–5) → (internal RLC size, transmitted RLC size) in bytes, per mode
_RLC_SIZES_VAES = {
    0b010: (2, 0),  # legacy: 16-bit implicit, rollover with window
    0b011: (2, 2),  # legacy: 16-bit explicit, rollover with window
    0b100: (3, 0),  # 24-bit implicit
    0b101: (3, 3),  # 24-bit explicit
    0b110: (4, 3),  # 32-bit internal, 24 LSb transmitted
    0b111: (4, 4),  # 32-bit explicit
}
_RLC_SIZES_CCM = {
    0b000: (4, 1),
    0b001: (4, 2),
    0b110: (4, 3),
    0b111: (4, 4),
}


@dataclass(frozen=True)
class SecurityLevelFormat:
    """A parsed SLF byte.

    Create one with ``SecurityLevelFormat.from_byte(value)``.
    """

    value: int
    """The SLF byte as transmitted."""

    mode: SecurityMode
    """The security mode (algorithm) used for this telegram."""

    mac_size: int
    """Size of the transmitted MAC in bytes (3 or 4)."""

    rlc_size: int
    """Size of the internal rolling code in bytes (2, 3 or 4)."""

    rlc_transmitted_size: int
    """Size of the rolling code part sent with each data telegram in bytes; 0 for implicit RLC."""

    @property
    def implicit_rlc(self) -> bool:
        """True iff data telegrams carry no RLC."""
        return self.rlc_transmitted_size == 0

    @property
    def reduced_rlc(self) -> bool:
        """True if data telegrams carry only the least significant part of the RLC (§6.3.3.2)."""
        return 0 < self.rlc_transmitted_size < self.rlc_size

    @property
    def rlc_rolls_over(self) -> bool:
        """True if the RLC wraps around to 0 and the receiver uses a window (Annex C.1).

        This applies to implicit RLC and to the legacy 16-bit explicit RLC; any other RLC never
        wraps around.
        """
        return self.implicit_rlc or self.rlc_size == 2

    @classmethod
    def from_byte(cls, value: int) -> "SecurityLevelFormat":
        """Parse an SLF byte; raises ``ValueError`` naming the reason if it is not supported.

        Supported are all values of Table 3 and the legacy VAES values of Annex C that use
        an RLC and a CMAC. Not supported: reserved field values, unencrypted telegrams, and
        legacy formats without RLC or CMAC (they give no replay protection or no
        authentication).
        """
        if not 0 <= value <= 0xFF:
            raise ValueError(f"SLF must be a byte, got {value}")

        mode_bits = value & 0b111
        mac_bits = (value >> 3) & 0b11
        rlc_bits = value >> 5

        if mode_bits == _MODE_VAES:
            mode = SecurityMode.VAES_CMAC
            rlc_sizes = _RLC_SIZES_VAES
        elif mode_bits == _MODE_CCM:
            mode = SecurityMode.CCM
            rlc_sizes = _RLC_SIZES_CCM
        elif mode_bits == 0b000:
            raise ValueError(f"SLF 0x{value:02X}: telegrams are not encrypted")
        else:
            raise ValueError(
                f"SLF 0x{value:02X}: reserved security mode 0b{mode_bits:03b}"
            )

        if mac_bits == 0b00:
            raise ValueError(f"SLF 0x{value:02X}: telegrams carry no CMAC")
        if mac_bits not in _MAC_SIZES:
            raise ValueError(f"SLF 0x{value:02X}: reserved MAC size 0b{mac_bits:02b}")
        mac_size = _MAC_SIZES[mac_bits]
        if mode is SecurityMode.CCM and mac_size != 4:
            raise ValueError(f"SLF 0x{value:02X}: CCM requires a 4-byte MAC")

        if mode is SecurityMode.VAES_CMAC and rlc_bits == 0b000:
            raise ValueError(f"SLF 0x{value:02X}: telegrams carry no RLC")
        if rlc_bits not in rlc_sizes:
            raise ValueError(
                f"SLF 0x{value:02X}: RLC size 0b{rlc_bits:03b} is reserved or not "
                f"defined for {mode.value}"
            )
        rlc_size, rlc_transmitted_size = rlc_sizes[rlc_bits]

        return cls(
            value=value,
            mode=mode,
            mac_size=mac_size,
            rlc_size=rlc_size,
            rlc_transmitted_size=rlc_transmitted_size,
        )

    def __str__(self) -> str:
        rlc = f"{self.rlc_size * 8}-bit RLC, " + (
            "implicit"
            if self.implicit_rlc
            else f"{self.rlc_transmitted_size * 8}-bit transmitted"
        )
        return (
            f"0x{self.value:02X} ({self.mode.value}, {self.mac_size}-byte MAC, {rlc})"
        )
