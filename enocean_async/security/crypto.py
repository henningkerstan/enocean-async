"""Cryptographic primitives of EnOcean security: VAES encryption and CMAC authentication.

Reference: *Security of EnOcean Radio Networks* V4.03, §7.1 (VAES) and §7.2 (CMAC,
RFC 4493). AES-128 and CMAC come from the ``cryptography`` package; this module only
arranges their inputs as the specification defines.
"""

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.cmac import CMAC

KEY_SIZE = 16
"""Size of a security key in bytes (AES-128)."""

BLOCK_SIZE = 16
"""AES block size in bytes."""

VAES_INIT_VECTOR = bytes.fromhex("3410DE8F1ABA3EFF9F5A117172EACABD")
"""Fixed VAES init vector (§7.1.4)."""


def _check_key_size(key: bytes) -> None:
    """Check that the key has the correct size; raise ValueError if not."""
    if len(key) != KEY_SIZE:
        raise ValueError(f"Security key must be {KEY_SIZE} bytes, got {len(key)}")


def _check_block_size(block: bytes) -> None:
    """Check that the block has the correct size; raise ValueError if not."""
    if len(block) != BLOCK_SIZE:
        raise ValueError(f"AES block must be {BLOCK_SIZE} bytes, got {len(block)}")


def _xor(a: bytes, b: bytes) -> bytes:
    """XOR two byte sequences of the same length."""
    return bytes(x ^ y for x, y in zip(a, b, strict=True))


def aes128_encrypt_block(key: bytes, block: bytes) -> bytes:
    """Encrypt one 16-byte block with AES-128."""
    _check_key_size(key)
    _check_block_size(block)
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return encryptor.update(block) + encryptor.finalize()


def vaes_encryption_vectors(key: bytes, rlc: bytes, count: int) -> list[bytes]:
    """Return the first ``count`` VAES encryption vectors for this key and RLC (§7.1.2, Figure 23).

    The variable init vector is the fixed init vector XOR the RLC, zero-padded to 16 bytes.
    Encryption vector 1 is AES(key, variable init vector); every further vector is
    AES(key, previous vector XOR variable init vector).
    """
    if not 0 < len(rlc) <= BLOCK_SIZE:
        raise ValueError(f"RLC must be 1 to {BLOCK_SIZE} bytes, got {len(rlc)}")
    variable_iv = _xor(VAES_INIT_VECTOR, rlc.ljust(BLOCK_SIZE, b"\x00"))
    vectors = [aes128_encrypt_block(key, variable_iv)]
    while len(vectors) < count:
        vectors.append(aes128_encrypt_block(key, _xor(vectors[-1], variable_iv)))
    return vectors


def vaes(key: bytes, rlc: bytes, payload: bytes) -> bytes:
    """Encrypt or decrypt ``payload`` with VAES (§7.1); the operation is its own inverse.

    ``rlc`` is the rolling code as big-endian bytes of its internal size (e.g. 3 bytes for a
    24-bit RLC). ``payload`` is the R-ORG (if present) followed by the DATA. Each 16-byte part
    of the payload is XORed with the matching encryption vector, truncated to its length.
    """
    if not payload:
        return b""
    count = -(-len(payload) // BLOCK_SIZE)  # number of 16-byte blocks, rounded up
    vectors = vaes_encryption_vectors(key, rlc, count)
    keystream = b"".join(vectors)[: len(payload)]
    return _xor(payload, keystream)


def cmac(key: bytes, data: bytes) -> bytes:
    """Return the full 16-byte AES-CMAC of ``data`` (§7.2, RFC 4493).

    A telegram carries only its most significant 3 or 4 bytes (the SLF's MAC size).
    """
    _check_key_size(key)
    c = CMAC(algorithms.AES(key))
    c.update(data)
    return c.finalize()
