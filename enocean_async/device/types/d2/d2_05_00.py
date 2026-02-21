"""Device type for D2-05-00 (position and angle)."""

from ....capabilities.position_angle import PositionAngleCapability
from ....eep.id import EEPID
from ...type import DeviceType

DEVICE_TYPE_D2_05_00 = DeviceType(
    eepid=EEPID.from_string("D2-05-00"),
    uid="d2-05-00",
    model="Blinds Control for Position and Angle",
    manufacturer="Generic",
    capability_factories=[
        lambda addr, cb: PositionAngleCapability(
            device_address=addr,
            on_state_change=cb,
        )
    ],
)
