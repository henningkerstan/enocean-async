"""A5-09: Gas Sensor.

A5-09-04: CO2 Sensor, with humidity and temperature.

Reference: EnOcean Equipment Profiles (EEP), A5-09-04. Used e.g. by the Eltako FCO2TS
(Eltako manual FCO2TS, 30 065 278 - 1: humidity 0–200 → 0–100 % in DB3, CO2 0–255 →
0–2550 ppm in DB2, temperature 0–255 → 0–51 °C in DB1).

Telegram layout (4 data bytes = 32 bits, DB3…DB0):
┌──────┬─────────┬──────┬──────────────────────────────────────────────────────┐
│ Name │  Bits   │  DB  │ Description                                          │
├──────┼─────────┼──────┼──────────────────────────────────────────────────────┤
│ HUM  │  0– 7   │ DB3  │ Rel. humidity: 0–200 → 0–100 %                       │
│ CONC │  8–15   │ DB2  │ CO2 concentration: 0–255 → 0–2550 ppm                │
│ TMP  │ 16–23   │ DB1  │ Temperature: 0–255 → 0–51.0 °C                       │
│ LRNB │    28   │ DB0  │ LRN bit: 0=teach-in telegram, 1=data telegram        │
│ HSN  │    29   │ DB0  │ Humidity sensor: 0=not available, 1=available        │
│ TSN  │    30   │ DB0  │ Temperature sensor: 0=not available, 1=available     │
└──────┴─────────┴──────┴──────────────────────────────────────────────────────┘
"""

from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..message import ValueWithContext
from ..profile import EEPDataField, Entity, SimpleProfileSpecification

_HUM_MAX = 200
_AVAILABILITY = {0: "Not available", 1: "Available"}


def _resolve_humidity(
    raw: dict, scaled: dict, _config: dict
) -> ValueWithContext | None:
    """Give the humidity only if the device has a humidity sensor."""
    if raw.get("HSN") != 1 or raw.get("HUM", _HUM_MAX + 1) > _HUM_MAX:
        return None
    return scaled.get("HUM")


def _resolve_temperature(
    raw: dict, scaled: dict, _config: dict
) -> ValueWithContext | None:
    """Give the temperature only if the device has a temperature sensor."""
    if raw.get("TSN") != 1:
        return None
    return scaled.get("TMP")


EEP_A5_09_04 = SimpleProfileSpecification(
    eep=EEP("A5-09-04"),
    name="CO2 sensor with humidity and temperature",
    datafields=[
        EEPDataField(
            id="HUM",
            name="Humidity",
            offset=0,
            size=8,
            range_max=_HUM_MAX,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 100.0,
            unit_fn=lambda _: "%",
        ),
        EEPDataField(
            id="CONC",
            name="CO2 concentration",
            offset=8,
            size=8,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 2550.0,
            unit_fn=lambda _: "ppm",
            observable=Observable.CO2,
        ),
        EEPDataField(
            id="TMP",
            name="Temperature",
            offset=16,
            size=8,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 51.0,
            unit_fn=lambda _: "°C",
        ),
        EEPDataField(
            id="LRNB",
            name="LRN bit",
            offset=28,
            size=1,
            range_enum={0: "Teach-in telegram", 1: "Data telegram"},
        ),
        EEPDataField(
            id="HSN",
            name="Humidity sensor",
            offset=29,
            size=1,
            range_enum=_AVAILABILITY,
        ),
        EEPDataField(
            id="TSN",
            name="Temperature sensor",
            offset=30,
            size=1,
            range_enum=_AVAILABILITY,
        ),
    ],
    semantic_resolvers={
        Observable.HUMIDITY: _resolve_humidity,
        Observable.TEMPERATURE: _resolve_temperature,
    },
    observers=[
        scalar_factory(Observable.CO2),
        scalar_factory(Observable.HUMIDITY),
        scalar_factory(Observable.TEMPERATURE),
    ],
    entities=[
        Entity(id="co2", observables=frozenset({Observable.CO2})),
        Entity(id="humidity", observables=frozenset({Observable.HUMIDITY})),
        Entity(id="temperature", observables=frozenset({Observable.TEMPERATURE})),
    ],
)

__all__ = ["EEP_A5_09_04"]
