"""Supply voltage fields whose valid range ends before the end of the byte.

Several 4BS profiles give the supply voltage a valid range of 0–250 (0–5.0 V) and reserve
251–255 for error codes (e.g. A5-07-01…03, A5-10-1A/1B/1E, A5-14-01…06; A5-14-09 gives
the valid range only). Such a value is not a voltage and must give none.
"""

from ..message import ValueWithContext
from ..profile import SemanticResolver

SUPPLY_VOLTAGE_MAX = 250
"""Largest valid raw value of such a supply voltage field (5.0 V)."""


def supply_voltage_resolver(field_id: str) -> SemanticResolver:
    """Return a resolver that gives the field's voltage only within its valid range 0–250."""

    def resolve(raw: dict, scaled: dict, _config: dict) -> ValueWithContext | None:
        if raw.get(field_id, SUPPLY_VOLTAGE_MAX + 1) > SUPPLY_VOLTAGE_MAX:
            return None
        return scaled.get(field_id)

    return resolve
