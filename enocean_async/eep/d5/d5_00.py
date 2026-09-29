"""D5-00: Contacts and Switches, Single Input Contact
"""

from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..profile import EEPDataField, Entity, SimpleProfileSpecification

EEP_D5_00_01 = SimpleProfileSpecification(
    eep=EEP("D5-00-01"),
    name="Single Input Contact",
    datafields=[
        EEPDataField(
            id="CO",
            name="Contact",
            offset=7,
            size=1,
            range_enum={0: "Open", 1: "Closed"},
            observable=Observable.CONTACT_STATE,
        )
    ],
    observers=[scalar_factory(Observable.CONTACT_STATE)],
    entities=[Entity(id=Observable.CONTACT_STATE.value, observables=frozenset({Observable.CONTACT_STATE}))],
)
