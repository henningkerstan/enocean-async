"""Typed commands for electronic switches and dimmers (D2-01)."""

from dataclasses import dataclass
from typing import ClassVar

from ..instructable import Instructable
from ..instruction import Instruction


@dataclass
class SetSwitchOutput(Instruction):
    """Set the output value of one or all channels of a D2-01 actuator (CMD 0x1)."""

    action: ClassVar[Instructable] = Instructable.SET_SWITCH_OUTPUT

    output_value: int
    """OV field: 0=OFF, 1–100=percentage ON, 0x7F=output value not valid/not applicable."""

    dim_value: int = 0
    """DV field: 0=switch to new output value immediately, 1–3=dim with timer 1–3, 4=stop dimming."""


@dataclass
class QueryActuatorStatus(Instruction):
    """Request the status of one or all channels of a D2-01 actuator (CMD 0x3)."""

    action: ClassVar[Instructable] = Instructable.QUERY_ACTUATOR_STATUS


@dataclass
class QueryActuatorMeasurement(Instruction):
    """Request an energy or power measurement from a D2-01 actuator (CMD 0x6)."""

    action: ClassVar[Instructable] = Instructable.QUERY_ACTUATOR_MEASUREMENT

    query_power: bool = False
    """qu field: False=query energy, True=query power."""
