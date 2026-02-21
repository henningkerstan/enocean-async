"""Device types for F6-02-01 and F6-02-02 rocker switch profiles."""

from ....capabilities.push_button import F6_02_01_02PushButtonCapability
from ....eep.id import EEPID
from ...type import DeviceType

DEVICE_TYPE_F6_02_01 = DeviceType(
    eepid=EEPID.from_string("F6-02-01"),
    uid="f6-02-01",
    model="4BS Rocker Switch 2-Channel",
    manufacturer="Generic",
    capability_factories=[
        lambda addr, cb: F6_02_01_02PushButtonCapability(
            device_address=addr,
            on_state_change=cb,
        )
    ],
)

DEVICE_TYPE_F6_02_02 = DeviceType(
    eepid=EEPID.from_string("F6-02-02"),
    uid="f6-02-02",
    model="4BS Rocker Switch 2-Channel",
    manufacturer="Generic",
    capability_factories=[
        lambda addr, cb: F6_02_01_02PushButtonCapability(
            device_address=addr,
            on_state_change=cb,
        )
    ],
)
