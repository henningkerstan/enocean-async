"""Device types for F6-10-00 window handle profiles."""

from dataclasses import dataclass

from ....capabilities.metadata import MetaDataCapability
from ....capabilities.window_state import WindowStateCapability
from ....eep.id import EEPID
from ....eep.manufacturer import Manufacturer
from ...type import DeviceType


@dataclass
class DeviceTypeF6_10_00(DeviceType):
    """Device type for F6-10-00 window handle sensor variants."""

    def __init__(self, type_: int, model: str, manufacturer: str = "Generic"):
        type_suffix = f"{type_:02X}"
        super().__init__(
            eepid=EEPID.from_string(f"F6-10-{type_suffix}"),
            uid=f"f6-10-{type_suffix.lower()}",
            model=model,
            manufacturer=manufacturer,
            capability_factories=[
                lambda addr, cb: WindowStateCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
                lambda addr, cb: MetaDataCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
            ],
        )


DEVICE_TYPE_F6_10_00 = DeviceTypeF6_10_00(
    type_=0x00,
    model="Window handle position sensor",
)

DEVICE_TYPE_F6_10_00_ELTAKO = DeviceTypeF6_10_00(
    type_=0x00,
    model="Window handle position sensor (Eltako variant)",
    manufacturer=Manufacturer.ELTAKO.name,
)
DEVICE_TYPE_F6_10_00_ELTAKO.eepid = EEPID(
    rorg=0xF6,
    func=0x10,
    type_=0x00,
    manufacturer=Manufacturer.ELTAKO,
)
