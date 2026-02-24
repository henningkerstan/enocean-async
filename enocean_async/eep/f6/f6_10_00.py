from enocean_async.eep.manufacturer import Manufacturer

from ...capabilities.entity_uids import EntityUID
from ...capabilities.scalar_sensor import ScalarSensorCapability
from ..id import EEPID
from ..profile import EEPDataField, SingleTelegramEEP

_WIN_FACTORIES = [
    lambda addr, cb: ScalarSensorCapability(
        device_address=addr,
        on_state_change=cb,
        entity_uid=EntityUID.WINDOW_STATE,
    ),
]

EEP_F6_10_00 = SingleTelegramEEP(
    id=EEPID.from_string("F6-10-00"),
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
            entity_uid=EntityUID.WINDOW_STATE,
        ),
    ],
    capability_factories=_WIN_FACTORIES,
)

EEP_F6_10_00_ELTAKO = SingleTelegramEEP(
    id=EEPID(rorg=0xF6, func=0x10, type_=0x00, manufacturer=Manufacturer.ELTAKO),
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
            entity_uid=EntityUID.WINDOW_STATE,
        ),
    ],
    capability_factories=_WIN_FACTORIES,
)
