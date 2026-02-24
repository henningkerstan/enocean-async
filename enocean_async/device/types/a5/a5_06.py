"""Device types for A5-06-XX light sensor profiles."""

from dataclasses import dataclass

from ....capabilities.illumination_sensor import IlluminationSensorCapability
from ....capabilities.metadata import MetaDataCapability
from ....eep.id import EEPID
from ....eep.manufacturer import Manufacturer
from ...type import DeviceType


@dataclass
class DeviceTypeA5_06(DeviceType):
    """Device type for A5-06-XX light sensor variants."""

    def __init__(self, type_: int, model: str, manufacturer: str = "Generic"):
        type_suffix = f"{type_:02X}"
        super().__init__(
            eepid=EEPID.from_string(f"A5-06-{type_suffix}"),
            uid=f"a5-06-{type_suffix.lower()}",
            model=model,
            manufacturer=manufacturer,
            capability_factories=[
                lambda addr, cb: IlluminationSensorCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
                lambda addr, cb: MetaDataCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
            ],
        )


DEVICE_TYPE_A5_06_01 = DeviceTypeA5_06(
    type_=0x01,
    model="Light sensor, range 300lx to 60000lx",
)
DEVICE_TYPE_A5_06_02 = DeviceTypeA5_06(
    type_=0x02,
    model="Light sensor, range 0lx to 1020lx",
)
DEVICE_TYPE_A5_06_03 = DeviceTypeA5_06(
    type_=0x03,
    model="Light sensor, 10-bit measurement, range 0lx to 1000lx",
)
DEVICE_TYPE_A5_06_04 = DeviceTypeA5_06(
    type_=0x04,
    model="Curtain wall brightness sensor",
)
DEVICE_TYPE_A5_06_05 = DeviceTypeA5_06(
    type_=0x05,
    model="Light sensor, range 0lx to 10200lx",
)

DEVICE_TYPE_A5_06_01_ELTAKO = DeviceTypeA5_06(
    type_=0x01,
    model="Light sensor, Eltako variant",
    manufacturer=Manufacturer.ELTAKO.name,
)
DEVICE_TYPE_A5_06_01_ELTAKO.eepid = EEPID(
    rorg=0xA5,
    func=0x06,
    type_=0x01,
    manufacturer=Manufacturer.ELTAKO,
)


__all__ = [
    "DEVICE_TYPE_A5_06_01",
    "DEVICE_TYPE_A5_06_01_ELTAKO",
    "DEVICE_TYPE_A5_06_02",
    "DEVICE_TYPE_A5_06_03",
    "DEVICE_TYPE_A5_06_04",
    "DEVICE_TYPE_A5_06_05",
]
