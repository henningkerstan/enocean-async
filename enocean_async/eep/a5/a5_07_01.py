"""A5-07-01: Occupancy with supply voltage monitor.

Reference: EnOcean Equipment Profiles (EEP), A5-07-01. Used e.g. by the Eltako FB65B
(Eltako manual FB65B, 30 065 470 - 1: DB1=0xC8 for semi-automatic and 0xFF for fully
automatic motion detection, DB0=0x08).

Telegram layout (4 data bytes = 32 bits, DB3…DB0):
┌──────┬─────────┬──────┬──────────────────────────────────────────────────────┐
│ Name │  Bits   │  DB  │ Description                                          │
├──────┼─────────┼──────┼──────────────────────────────────────────────────────┤
│ SVC  │  0– 7   │ DB3  │ Supply voltage (optional): 0–250 → 0–5.0 V;          │
│      │         │      │ 251–255 reserved for error codes                     │
│ PIRS │ 16–23   │ DB1  │ PIR status: 0–127=PIR off, 128–255=PIR on            │
│ LRNB │    28   │ DB0  │ LRN bit: 0=teach-in telegram, 1=data telegram        │
│ SVA  │    31   │ DB0  │ Supply voltage availability: 0=not supported,        │
│      │         │      │ 1=supported                                          │
└──────┴─────────┴──────┴──────────────────────────────────────────────────────┘
"""

from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..message import ValueWithContext
from ..profile import EEPDataField, Entity, SimpleProfileSpecification

_SVC_MAX = 250
_PIR_ON = frozenset(range(128, 256))


def _resolve_supply_voltage(
    raw: dict, scaled: dict, _config: dict
) -> ValueWithContext | None:
    """Give the supply voltage only if the device supports it and reports no error code."""
    if raw.get("SVA") != 1 or raw.get("SVC", _SVC_MAX + 1) > _SVC_MAX:
        return None
    return scaled.get("SVC")


EEP_A5_07_01 = SimpleProfileSpecification(
    eep=EEP("A5-07-01"),
    name="Occupancy with supply voltage monitor",
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
            id="PIRS",
            name="PIR status",
            offset=16,
            size=8,
            observable=Observable.MOTION,
            true_values=_PIR_ON,
        ),
        EEPDataField(
            id="LRNB",
            name="LRN bit",
            offset=28,
            size=1,
            range_enum={0: "Teach-in telegram", 1: "Data telegram"},
        ),
        EEPDataField(
            id="SVA",
            name="Supply voltage availability",
            offset=31,
            size=1,
            range_enum={
                0: "Supply voltage is not supported",
                1: "Supply voltage is supported",
            },
        ),
    ],
    semantic_resolvers={Observable.VOLTAGE: _resolve_supply_voltage},
    observers=[
        scalar_factory(Observable.VOLTAGE, entity_id="supply_voltage"),
        scalar_factory(Observable.MOTION),
    ],
    entities=[
        Entity(id="supply_voltage", observables=frozenset({Observable.VOLTAGE})),
        Entity(id="motion", observables=frozenset({Observable.MOTION})),
    ],
)

__all__ = ["EEP_A5_07_01"]
