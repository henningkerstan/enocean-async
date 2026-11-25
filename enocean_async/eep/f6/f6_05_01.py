"""F6-05-01: Liquid leakage sensor (mechanic harvester)."""

from ...semantics.observable import Observable
from ...semantics.observers.scalar import scalar_factory
from ..id import EEP
from ..manufacturer import Manufacturer
from ..profile import EEPDataField, EEPSpecification, EEPTelegram, Entity

_WATER_SENSOR = 0x11


def _spec(eep: EEP, name: str, nu_enum: dict[int, str]) -> EEPSpecification:
    # The data byte selects the telegram, so that any other data byte is ignored.
    return EEPSpecification(
        eep=eep,
        name=name,
        cmd_offset=0,
        cmd_size=8,
        telegrams={
            _WATER_SENSOR: EEPTelegram(
                "Water sensor",
                [
                    EEPDataField(
                        id="WAS",
                        name="Water sensor",
                        offset=0,
                        size=8,
                        range_enum={_WATER_SENSOR: "Water detected"},
                    ),
                    EEPDataField(
                        id="NU",
                        name="Water detected",
                        offset=3,
                        size=1,
                        in_status=True,
                        range_enum=nu_enum,
                        observable=Observable.WATER_DETECTED,
                        true_values=frozenset({1}),
                    ),
                ],
            )
        },
        observers=[scalar_factory(Observable.WATER_DETECTED)],
        entities=[
            Entity(
                id=Observable.WATER_DETECTED.value,
                observables=frozenset({Observable.WATER_DETECTED}),
            )
        ],
    )


# The EEP specification defines one telegram only: water detected, with NU = 1 in the status
# byte. A device which follows it never reports that the water is gone.
EEP_F6_05_01 = _spec(
    EEP("F6-05-01"),
    "Liquid leakage sensor (mechanic harvester)",
    {1: "Water detected"},
)

# Eltako FWS81: the data byte is 0x11 in both telegrams; the status byte tells them apart,
# 0x30 (NU = 1) for water and 0x20 (NU = 0) for no water.
EEP_F6_05_01_ELTAKO = _spec(
    EEP("F6-05-01", Manufacturer.ELTAKO),
    "Liquid leakage sensor, Eltako variant (FWS81)",
    {0: "No water", 1: "Water detected"},
)
