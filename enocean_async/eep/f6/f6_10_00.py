from enocean_async.eep.manufacturer import Manufacturer

from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..profile import EEPDataField, Entity, SimpleProfileSpecification

_WIN_FACTORIES = [scalar_factory(Observable.WINDOW_STATE)]
_WIN_ENTITIES = [
    Entity(id="window_state", observables=frozenset({Observable.WINDOW_STATE}))
]

EEP_F6_10_00 = SimpleProfileSpecification(
    eep=EEP("F6-10-00"),
    name="Window handle",
    datafields=[
        EEPDataField(
            id="WIN",
            name="Window state",
            offset=2,
            size=2,
            # the EEP spec has a lot of different variants of the window handle state; for brevity and clarity we use the resulting state of the window
            range_enum={
                0: "open",  # was tilted, now open
                1: "tilted",  # tilted open
                2: "open",  # was closed, now open
                3: "closed",  # "window now closed"
            },
            observable=Observable.WINDOW_STATE,
        ),
    ],
    observers=_WIN_FACTORIES,
    entities=_WIN_ENTITIES,
)

EEP_F6_10_00_ELTAKO = SimpleProfileSpecification(
    eep=EEP("F6-10-00", Manufacturer.ELTAKO),
    name="Window handle (Eltako variant)",
    datafields=[
        EEPDataField(
            id="WIN",
            name="Window state",
            offset=0,
            size=8,
            range_enum={
                0xD0: "tilted",
                0xE0: "open",
                0xF0: "closed",
            },
            observable=Observable.WINDOW_STATE,
        ),
    ],
    observers=_WIN_FACTORIES,
    entities=_WIN_ENTITIES,
)
