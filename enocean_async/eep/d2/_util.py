"""Shared helpers for D2 (VLD) profile modules."""


def channel_from_entity_id(entity_id: str, *, default: int) -> int:
    """Resolve an action's entity_id of the form ``"ch<N>_<suffix>"`` (1-indexed)
    to a 0-indexed channel value.

    Returns ``default`` for anything else: a device's shared
    single-channel entity id that carries no channel number (e.g. D2-05's
    ``"cover"``), or any other unrecognized id.
    """
    if entity_id.startswith("ch"):
        digits = entity_id[2:].partition("_")[0]
        if digits.isdigit():
            return int(digits) - 1
    return default
