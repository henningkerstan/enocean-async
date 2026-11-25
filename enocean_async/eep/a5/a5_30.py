"""A5-30-XX: Digital input."""

from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..profile import EEPDataField, Entity, SimpleProfileSpecification

_BATTERY_LOW = range(0, 121)
_CONTACT_CLOSED = range(0, 196)
_CONTACT_OPEN = range(196, 256)

_SVC = EEPDataField(
    id="SVC",
    name="Supply voltage",
    offset=8,
    size=8,
    range_enum={
        **{i: "Battery LOW" for i in _BATTERY_LOW},
        **{i: "Battery OK" for i in range(121, 256)},
    },
    observable=Observable.BATTERY_LOW,
    true_values=frozenset(_BATTERY_LOW),
)

_IPS_ENUM = {
    **{i: "Contact closed" for i in _CONTACT_CLOSED},
    **{i: "Contact open" for i in _CONTACT_OPEN},
}

_BATTERY_ENTITY = Entity(
    id=Observable.BATTERY_LOW.value, observables=frozenset({Observable.BATTERY_LOW})
)
_WATER_ENTITY = Entity(
    id=Observable.WATER_DETECTED.value,
    observables=frozenset({Observable.WATER_DETECTED}),
)


def _digital_input(shortcut: str, name: str, offset: int) -> EEPDataField:
    return EEPDataField(
        id=shortcut,
        name=name,
        offset=offset,
        size=1,
        range_enum={0: "Low", 1: "High"},
    )


EEP_A5_30_01 = SimpleProfileSpecification(
    eep=EEP("A5-30-01"),
    name="Single input contact, battery monitor",
    datafields=[
        _SVC,
        EEPDataField(
            id="IPS",
            name="Input state",
            offset=16,
            size=8,
            range_enum=_IPS_ENUM,
            observable=Observable.CONTACT_STATE,
            true_values=frozenset(_CONTACT_OPEN),
        ),
    ],
    observers=[
        scalar_factory(Observable.BATTERY_LOW),
        scalar_factory(Observable.CONTACT_STATE),
    ],
    entities=[
        _BATTERY_ENTITY,
        Entity(
            id=Observable.CONTACT_STATE.value,
            observables=frozenset({Observable.CONTACT_STATE}),
        ),
    ],
)

# The digital inputs and the wake signal have no observable: what they mean depends on
# the application and is not defined by the profile.
EEP_A5_30_03 = SimpleProfileSpecification(
    eep=EEP("A5-30-03"),
    name="4 digital inputs, wake and temperature",
    datafields=[
        EEPDataField(
            id="TMP",
            name="Temperature",
            offset=8,
            size=8,
            range_min=255,
            range_max=0,
            scale_min_fn=lambda _: 0.0,
            scale_max_fn=lambda _: 40.0,
            unit_fn=lambda _: "°C",
            observable=Observable.TEMPERATURE,
        ),
        _digital_input("WA0", "Status of wake", 19),
        _digital_input("DI3", "Digital input 3", 20),
        _digital_input("DI2", "Digital input 2", 21),
        _digital_input("DI1", "Digital input 1", 22),
        _digital_input("DI0", "Digital input 0", 23),
    ],
    observers=[scalar_factory(Observable.TEMPERATURE)],
    entities=[
        Entity(id="temperature", observables=frozenset({Observable.TEMPERATURE}))
    ],
)

# Eltako FSM60B: a transmitter module for the conductive water probe FWS60. A jumper selects
# what it sends: A5-30-03 (factory setting) or A5-30-01, which also carries the battery state.

# The EEP specification names this application: "water sensor conductive – Wake Status = 0
# (water detected)". The Eltako telegram list gives DB1 = 0x0F / 0x1F, which differ in the
# wake bit only.
EEP_A5_30_03_ELTAKO_FSM60B = SimpleProfileSpecification(
    eep=EEP("A5-30-03.ELTAKO.FSM60B"),
    name="Water sensor, Eltako FSM60B with FWS60 (A5-30-03, factory setting)",
    datafields=[
        EEPDataField(
            id="WA0",
            name="Status of wake",
            offset=19,
            size=1,
            range_enum={0: "Water detected", 1: "No water"},
            observable=Observable.WATER_DETECTED,
            true_values=frozenset({0}),
        ),
    ],
    observers=[scalar_factory(Observable.WATER_DETECTED)],
    entities=[_WATER_ENTITY],
)

# The Eltako telegram list gives DB1 = 0x00 / 0xFF and does not say which one means water.
# Water between the electrodes of a conductive probe closes the contact, so "contact closed"
# is taken as water. Not confirmed on a device.
EEP_A5_30_01_ELTAKO_FSM60B = SimpleProfileSpecification(
    eep=EEP("A5-30-01.ELTAKO.FSM60B"),
    name="Water sensor, Eltako FSM60B with FWS60 (A5-30-01)",
    datafields=[
        _SVC,
        EEPDataField(
            id="IPS",
            name="Input state",
            offset=16,
            size=8,
            range_enum=_IPS_ENUM,
            observable=Observable.WATER_DETECTED,
            true_values=frozenset(_CONTACT_CLOSED),
        ),
    ],
    observers=[
        scalar_factory(Observable.BATTERY_LOW),
        scalar_factory(Observable.WATER_DETECTED),
    ],
    entities=[_BATTERY_ENTITY, _WATER_ENTITY],
)
