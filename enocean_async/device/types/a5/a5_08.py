"""Device types for A5-08-XX light, temperature and occupancy sensor profiles."""

from dataclasses import dataclass

from ....capabilities.illumination_sensor import IlluminationSensorCapability
from ....capabilities.metadata import MetaDataCapability
from ....capabilities.motion_sensor import MotionSensorCapability
from ....capabilities.push_button import PushButtonCapability
from ....capabilities.temperature_sensor import TemperatureSensorCapability
from ....capabilities.voltage_sensor import VoltageSensorCapability
from ....eep.id import EEPID
from ....eep.manufacturer import Manufacturer
from ...type import DeviceType


@dataclass
class DeviceTypeA5_08(DeviceType):
    """Device type for A5-08-XX light, temperature and occupancy sensor variants."""

    def __init__(self, type_: int, ill_max: float, temp_min: float, temp_max: float):
        type_suffix = f"{type_:02X}"
        super().__init__(
            eepid=EEPID.from_string(f"A5-08-{type_suffix}"),
            uid=f"a5-08-{type_suffix.lower()}",
            model=f"Light, temperature and occupancy sensor, range 0lx to {ill_max}lx, {temp_min}°C to {temp_max}°C and occupancy button",
            manufacturer="Generic",
            capability_factories=[
                lambda addr, cb: VoltageSensorCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
                lambda addr, cb: IlluminationSensorCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
                lambda addr, cb: TemperatureSensorCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
                lambda addr, cb: MotionSensorCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
                lambda addr, cb: PushButtonCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
                lambda addr, cb: MetaDataCapability(
                    device_address=addr,
                    on_state_change=cb,
                ),
            ],
        )


DEVICE_TYPE_A5_08_01 = DeviceTypeA5_08(
    type_=0x01, ill_max=510, temp_min=0.0, temp_max=51.0
)
DEVICE_TYPE_A5_08_02 = DeviceTypeA5_08(
    type_=0x02, ill_max=1020, temp_min=0.0, temp_max=51.0
)
DEVICE_TYPE_A5_08_03 = DeviceTypeA5_08(
    type_=0x03, ill_max=1530, temp_min=-30.0, temp_max=50.0
)

DEVICE_TYPE_A5_08_01_ELTAKO = DeviceType(
    eepid=EEPID(0xA5, 0x08, 0x01, manufacturer=Manufacturer.ELTAKO),
    uid="a5-08-01-eltako",
    model="Light and occupancy sensor, range 0lx to 510lx, Eltako variant",
    manufacturer="Eltako",
    capability_factories=[
        lambda addr, cb: VoltageSensorCapability(
            device_address=addr,
            on_state_change=cb,
        ),
        lambda addr, cb: IlluminationSensorCapability(
            device_address=addr,
            on_state_change=cb,
        ),
        lambda addr, cb: MotionSensorCapability(
            device_address=addr,
            on_state_change=cb,
        ),
        lambda addr, cb: MetaDataCapability(
            device_address=addr,
            on_state_change=cb,
        ),
    ],
)

__all__ = [
    "DEVICE_TYPE_A5_08_01",
    "DEVICE_TYPE_A5_08_01_ELTAKO",
    "DEVICE_TYPE_A5_08_02",
    "DEVICE_TYPE_A5_08_03",
]
