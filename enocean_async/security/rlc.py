"""Rolling code (RLC) tracking on the receiving side.

Reference: *Security of EnOcean Radio Networks* V4.03, §6.3 and Annex C.1.

The receiver stores RLC_R, the lowest acceptable RLC of a sender (§6.3.2). For each received
telegram, ``rlc_candidates`` gives the RLC values to try, in order; the first one with which the
telegram authenticates is the one the sender used, and ``next_rlc`` gives the new RLC_R. A
telegram for which no candidate authenticates is rejected and RLC_R stays unchanged.
"""

from collections.abc import Iterator

from .slf import SecurityLevelFormat

RLC_WINDOW = 128
"""Number of RLC values tried for implicit and rolling-over RLC (§6.3.3.3): the expected one and
the 127 following ones."""


def rlc_to_bytes(rlc: int, slf: SecurityLevelFormat) -> bytes:
    """Return the RLC as big-endian bytes of its internal size, as VAES and CMAC use it."""
    return rlc.to_bytes(slf.rlc_size, "big")


def rlc_candidates(
    slf: SecurityLevelFormat,
    lowest_acceptable: int,
    transmitted: int | None,
    window: int = RLC_WINDOW,
) -> Iterator[int]:
    """Yield the RLC values to try for a received telegram, with most likely first.

    Args:
        slf: The sender's security level format.
        lowest_acceptable: The stored RLC_R of the sender.
        transmitted: The RLC (part) carried by the telegram, or ``None`` for implicit RLC.
        window: Number of values tried where the RLC is not (fully) transmitted.

    Yields nothing if the telegram cannot be accepted, e.g. because its RLC is below RLC_R.
    """
    modulus = 1 << (8 * slf.rlc_size)
    # RLC_R equals the modulus once an RLC that does not roll over is used up (see next_rlc)
    highest_rlc_r = modulus - 1 if slf.rlc_rolls_over else modulus
    if not 0 <= lowest_acceptable <= highest_rlc_r:
        raise ValueError(
            f"RLC_R 0x{lowest_acceptable:X} does not fit a {slf.rlc_size * 8}-bit RLC"
        )
    if slf.implicit_rlc != (transmitted is None):
        raise ValueError(
            "a transmitted RLC is required unless the RLC is implicit, and must be absent if it is"
        )

    if slf.implicit_rlc:
        # §6.3.3.3: try the expected RLC and the following ones; implicit RLC rolls over
        for offset in range(window):
            yield (lowest_acceptable + offset) % modulus
        return

    assert transmitted is not None
    if not 0 <= transmitted < 1 << (8 * slf.rlc_transmitted_size):
        raise ValueError(
            f"transmitted RLC 0x{transmitted:X} does not fit "
            f"{slf.rlc_transmitted_size} bytes"
        )

    if slf.reduced_rlc:
        # §6.3.3.2: complete the transmitted least significant part with the stored upper part,
        # incremented by one if the transmitted part is below the stored one
        part_modulus = 1 << (8 * slf.rlc_transmitted_size)
        upper = lowest_acceptable - lowest_acceptable % part_modulus
        if transmitted < lowest_acceptable % part_modulus:
            upper += part_modulus
        rlc = upper + transmitted
        if rlc < modulus:
            yield rlc
        return

    if slf.rlc_rolls_over:
        # legacy 16-bit explicit RLC (Annex C.1): rolls over, accepted within the window
        if (transmitted - lowest_acceptable) % modulus < window:
            yield transmitted
        return

    # full RLC transmitted (§6.3.2): accepted if not below RLC_R
    if transmitted >= lowest_acceptable:
        yield transmitted


def next_rlc(slf: SecurityLevelFormat, rlc: int) -> int:
    """Return the new RLC_R after a telegram with ``rlc`` authenticated: ``rlc`` + 1 (§6.3.2).

    An RLC that rolls over wraps to 0. One that does not cannot go beyond its maximum; the
    result is then the modulus itself, which no further telegram can reach.
    """
    modulus = 1 << (8 * slf.rlc_size)
    if slf.rlc_rolls_over:
        return (rlc + 1) % modulus
    return rlc + 1
