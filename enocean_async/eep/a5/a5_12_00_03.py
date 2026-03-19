"""A5-12-XX: Automated meter reading (AMR) — counter, electricity, gas, water."""

from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..message import ValueWithContext
from ..profile import EEPDataField, Entity, SimpleProfileSpecification


def _compute_mr_scale_max(raw_values: dict[str, int]) -> float:
    """Compute MR scale_max based on DIV field value."""
    div_value = raw_values.get("DIV", 0)
    divisors = [1, 10, 100, 1000]
    divisor = divisors[div_value] if div_value < len(divisors) else 1
    return 16777215.0 / divisor


def _cumulative_resolver(unit: str | None):
    def resolver(
        raw: dict[str, int], scaled: dict[str, ValueWithContext]
    ) -> ValueWithContext | None:
        if raw.get("DT") != 0:
            return None
        mr = scaled.get("MR")
        return (
            ValueWithContext(value=mr.value, unit=unit, name="Cumulative value")
            if mr
            else None
        )

    return resolver


def _current_resolver(unit: str | None):
    def resolver(
        raw: dict[str, int], scaled: dict[str, ValueWithContext]
    ) -> ValueWithContext | None:
        if raw.get("DT") != 1:
            return None
        mr = scaled.get("MR")
        return (
            ValueWithContext(value=mr.value, unit=unit, name="Current value")
            if mr
            else None
        )

    return resolver


_AMR_CONFIGS = {
    0x00: (
        {
            Observable.COUNTER: _cumulative_resolver(None),
            Observable.COUNTER_RATE: _current_resolver(None),
        },
        [scalar_factory(Observable.COUNTER), scalar_factory(Observable.COUNTER_RATE)],
        [
            Entity("counter", frozenset({Observable.COUNTER})),
            Entity("counter_rate", frozenset({Observable.COUNTER_RATE})),
        ],
    ),
    0x01: (
        {
            Observable.ENERGY: _cumulative_resolver("Wh"),
            Observable.POWER: _current_resolver("W"),
        },
        [scalar_factory(Observable.ENERGY), scalar_factory(Observable.POWER)],
        [
            Entity("energy", frozenset({Observable.ENERGY})),
            Entity("power", frozenset({Observable.POWER})),
        ],
    ),
    0x02: (
        {
            Observable.GAS_VOLUME: _cumulative_resolver("m³"),
            Observable.GAS_FLOW: _current_resolver("l/s"),
        },
        [scalar_factory(Observable.GAS_VOLUME), scalar_factory(Observable.GAS_FLOW)],
        [
            Entity("gas_volume", frozenset({Observable.GAS_VOLUME})),
            Entity("gas_flow", frozenset({Observable.GAS_FLOW})),
        ],
    ),
    0x03: (
        {
            Observable.WATER_VOLUME: _cumulative_resolver("m³"),
            Observable.WATER_FLOW: _current_resolver("l/s"),
        },
        [
            scalar_factory(Observable.WATER_VOLUME),
            scalar_factory(Observable.WATER_FLOW),
        ],
        [
            Entity("water_volume", frozenset({Observable.WATER_VOLUME})),
            Entity("water_flow", frozenset({Observable.WATER_FLOW})),
        ],
    ),
}

_AMR_NAMES = {0x00: "counter", 0x01: "electricity", 0x02: "gas", 0x03: "water"}


class _EEP_A5_12_00_03(SimpleProfileSpecification):
    def __init__(self, _type: int, info_id: str, info_name: str):
        resolvers, observers, entities = _AMR_CONFIGS[_type]

        super().__init__(
            eep=EEP(f"A5-12-{_type:02X}"),
            name=f"Automated meter reading (AMR), {_AMR_NAMES[_type]}",
            datafields=[
                EEPDataField(
                    id="MR",
                    name="Meter reading",
                    offset=0,
                    size=24,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=_compute_mr_scale_max,
                ),
                EEPDataField(
                    id=info_id,
                    name=info_name,
                    offset=24,
                    size=4,
                    scale_min_fn=lambda _: 0.0,
                    scale_max_fn=lambda _: 15.0,
                    unit_fn=lambda _: "",
                ),
                EEPDataField(
                    id="DT",
                    name="Data type (unit)",
                    offset=29,
                    size=1,
                    range_enum={
                        0: "Cumulative value",
                        1: "Current value",
                    },
                ),
                EEPDataField(
                    id="DIV",
                    name="Divisor (scale)",
                    offset=30,
                    size=2,
                    range_enum={
                        0: "x/1",
                        1: "x/10",
                        2: "x/100",
                        3: "x/1000",
                    },
                ),
            ],
            semantic_resolvers=resolvers,
            observers=observers,
            entities=entities,
        )


EEP_A5_12_00 = _EEP_A5_12_00_03(
    _type=0x00, info_id="CH", info_name="Measurement channel"
)
EEP_A5_12_01 = _EEP_A5_12_00_03(_type=0x01, info_id="TI", info_name="Tariff info")
EEP_A5_12_02 = _EEP_A5_12_00_03(_type=0x02, info_id="TI", info_name="Tariff info")
EEP_A5_12_03 = _EEP_A5_12_00_03(_type=0x03, info_id="TI", info_name="Tariff info")
