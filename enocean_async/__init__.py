"""
An async implementation of the EnOcean Serial Protocol Version 3.
"""

__version__ = "0.10.0"
__date__ = "2026-03-23"

from .address import EURID, BaseAddress, BroadcastAddress, SenderAddress
from .device import Device
from .eep import DEVICE_TYPES, EEP_SPECIFICATIONS, DeviceType, device_type_for_eep
from .eep.id import EEP
from .eep.manufacturer import Manufacturer
from .gateway import DeviceTaughtInCallback, Gateway
from .semantics.device_spec import DeviceSpec
from .semantics.entity import (
    Entity,
    EntityCategory,
    EntityType,
    EnumOptions,
    NumberRange,
)
from .semantics.instructable import Instructable
from .semantics.instruction import Instruction
from .semantics.instructions.cover import (
    CoverClose,
    CoverOpen,
    CoverQueryPositionAndAngle,
    CoverSetPositionAndAngle,
    CoverStop,
)
from .semantics.instructions.dimmer import Dim, Switch
from .semantics.instructions.fan import SetFanSpeed
from .semantics.instructions.switch import (
    QueryActuatorMeasurement,
    QueryActuatorStatus,
    SetSwitchOutput,
)
from .semantics.observable import Observable
from .semantics.observation import Observation, ObservationCallback, ObservationSource
from .semantics.value_kind import ValueKind

__all__ = [
    # Gateway
    "Gateway",
    "DeviceTaughtInCallback",
    # Addresses
    "BaseAddress",
    "BroadcastAddress",
    "EURID",
    "SenderAddress",
    # Device / EEP
    "Device",
    "DeviceSpec",
    "DeviceType",
    "DEVICE_TYPES",
    "device_type_for_eep",
    "Entity",
    "EntityCategory",
    "EntityType",
    "EnumOptions",
    "NumberRange",
    "EEP",
    "EEP_SPECIFICATIONS",
    "Manufacturer",
    # Receive side
    "Observable",
    "Observation",
    "ObservationCallback",
    "ObservationSource",
    "ValueKind",
    # Send side
    "Instructable",
    "Instruction",
    "CoverClose",
    "CoverOpen",
    "CoverQueryPositionAndAngle",
    "CoverSetPositionAndAngle",
    "CoverStop",
    "Dim",
    "Switch",
    "QueryActuatorMeasurement",
    "QueryActuatorStatus",
    "SetFanSpeed",
    "SetSwitchOutput",
]
