"""A5-14: Multi-Func Sensor.

A5-14-09: Window/Door-Sensor with States Open/Closed/Tilt, Supply voltage monitor.

Reference: EnOcean Equipment Profiles (EEP), A5-14-09. Used e.g. by the Eltako FFG7B in
its delivery state (Eltako manual FFG7B, 30 000 443 - 2: closed=0x08, tilted=0x0A,
open=0x0E in DB0; supply voltage 0–250 → 0–5 V in DB3).

Telegram layout (4 data bytes = 32 bits, DB3…DB0):
┌──────┬─────────┬──────┬──────────────────────────────────────────────────────┐
│ Name │  Bits   │  DB  │ Description                                          │
├──────┼─────────┼──────┼──────────────────────────────────────────────────────┤
│ SVC  │  0– 7   │ DB3  │ Supply voltage: 0–250 → 0–5.0 V (valid range)        │
│ LRNB │    28   │ DB0  │ LRN bit: 0=teach-in telegram, 1=data telegram        │
│ CT   │ 29–30   │ DB0  │ Contact: 0=closed, 1=tilt, 2=reserved, 3=open        │
└──────┴─────────┴──────┴──────────────────────────────────────────────────────┘
"""

from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..message import ValueWithContext
from ..profile import EEPDataField, Entity, SimpleProfileSpecification

_SVC_MAX = 250
_WINDOW_STATES = {0: "closed", 1: "tilted", 3: "open"}


def _resolve_supply_voltage(
    raw: dict, scaled: dict, _config: dict
) -> ValueWithContext | None:
    """Give the supply voltage only within its valid range 0–250.

    A5-14-09 defines no meaning for 251–255; A5-14-01…06 reserve them for error codes.
    """
    if raw.get("SVC", _SVC_MAX + 1) > _SVC_MAX:
        return None
    return scaled.get("SVC")


def _resolve_window_state(
    raw: dict, _scaled: dict, _config: dict
) -> ValueWithContext | None:
    """Derive the window state from the contact field; the reserved value gives none."""
    if raw.get("LRNB") == 0:
        return None  # teach-in telegram, ignore
    state = _WINDOW_STATES.get(raw.get("CT", -1))
    if state is None:
        return None
    return ValueWithContext(name="Window state", value=state, unit=None)


EEP_A5_14_09 = SimpleProfileSpecification(
    eep=EEP("A5-14-09"),
    name="Window/door sensor with states open/closed/tilt, supply voltage monitor",
    datafields=[
        EEPDataField(
            id="SVC",
            name="Supply voltage",
            offset=0,
            size=8,
            range_max=_SVC_MAX,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 5.0,
            unit_fn=lambda _: "V",
        ),
        EEPDataField(
            id="LRNB",
            name="LRN bit",
            offset=28,
            size=1,
            range_enum={0: "Teach-in telegram", 1: "Data telegram"},
        ),
        EEPDataField(
            id="CT",
            name="Contact",
            offset=29,
            size=2,
            range_enum={0: "Closed", 1: "Tilt", 2: "Reserved", 3: "Open"},
        ),
    ],
    semantic_resolvers={
        Observable.VOLTAGE: _resolve_supply_voltage,
        Observable.WINDOW_STATE: _resolve_window_state,
    },
    observers=[
        scalar_factory(Observable.VOLTAGE, entity_id="supply_voltage"),
        scalar_factory(Observable.WINDOW_STATE),
    ],
    entities=[
        Entity(id="supply_voltage", observables=frozenset({Observable.VOLTAGE})),
        Entity(id="window_state", observables=frozenset({Observable.WINDOW_STATE})),
    ],
)

__all__ = ["EEP_A5_14_09"]
