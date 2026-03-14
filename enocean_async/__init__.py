"""
An async implementation of the EnOcean Serial Protocol Version 3.
"""

__version__ = "0.7.0-dev0"
__date__ = "2026-03-13"

from .address import EURID, BaseAddress, BroadcastAddress, SenderAddress
from .device import Device
from .eep import EEP_SPECIFICATIONS
from .eep.id import EEP
from .eep.manufacturer import Manufacturer
from .eep.profile import DeviceDescriptor, Entity
from .gateway import DeviceTaughtInCallback, Gateway
from .semantics.entity_type import EntityType
from .semantics.instructable import Instructable
from .semantics.instruction import Instruction
from .semantics.instructions.cover import (
    QueryCoverPosition,
    SetCoverPosition,
    StopCover,
)
from .semantics.instructions.dimmer import Dim
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
    "DeviceDescriptor",
    "Entity",
    "EEP",
    "EEP_SPECIFICATIONS",
    "Manufacturer",
    # Receive side
    "EntityType",
    "Observable",
    "Observation",
    "ObservationCallback",
    "ObservationSource",
    "ValueKind",
    # Send side
    "Instructable",
    "Instruction",
    "Dim",
    "QueryActuatorMeasurement",
    "QueryActuatorStatus",
    "QueryCoverPosition",
    "SetCoverPosition",
    "SetFanSpeed",
    "SetSwitchOutput",
    "StopCover",
]
