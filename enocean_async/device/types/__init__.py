"""Device types mapped by EEPID.

This module provides a registry of DeviceType instances organized by RORG (Radio Telegram Type).
Each DeviceType declares the capabilities available for that EEP profile.
"""

from ...eep.id import EEPID
from ..type import DeviceType
from .d2 import DEVICE_TYPE_D2_05_00
from .f6 import DEVICE_TYPE_F6_02_01, DEVICE_TYPE_F6_02_02

DEVICE_TYPE_DATABASE: dict[EEPID, DeviceType] = {
    DEVICE_TYPE_D2_05_00.eepid: DEVICE_TYPE_D2_05_00,
    DEVICE_TYPE_F6_02_01.eepid: DEVICE_TYPE_F6_02_01,
    DEVICE_TYPE_F6_02_02.eepid: DEVICE_TYPE_F6_02_02,
}

__all__ = [
    "DEVICE_TYPE_DATABASE",
    "DEVICE_TYPE_D2_05_00",
    "DEVICE_TYPE_F6_02_01",
    "DEVICE_TYPE_F6_02_02",
]
