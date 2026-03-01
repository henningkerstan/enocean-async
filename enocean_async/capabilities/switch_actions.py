"""Typed actions for electronic switches and dimmers (D2-01)."""

from dataclasses import dataclass
from typing import ClassVar

from .action import Action
from .action_uid import ActionUID


@dataclass
class SetSwitchOutputAction(Action):
    """Set the output value of one or all channels of a D2-01 actuator (CMD 0x1)."""

    action_uid: ClassVar[str] = ActionUID.SET_SWITCH_OUTPUT

    output_value: int
    """OV field: 0=OFF, 1–100=percentage ON, 0x7F=output value not valid/not applicable."""

    channel: int = 0x1E
    """I/O field: 0x00–0x1D=specific channel, 0x1E=all channels, 0x1F=input channel."""

    dim_value: int = 0
    """DV field: 0=switch to new output value immediately, 1–3=dim with timer 1–3, 4=stop dimming."""


@dataclass
class QueryActuatorStatusAction(Action):
    """Request the status of one or all channels of a D2-01 actuator (CMD 0x3)."""

    action_uid: ClassVar[str] = ActionUID.QUERY_ACTUATOR_STATUS

    channel: int = 0x1E
    """I/O field: 0x00–0x1D=specific channel, 0x1E=all channels, 0x1F=input channel."""


@dataclass
class QueryActuatorMeasurementAction(Action):
    """Request an energy or power measurement from a D2-01 actuator (CMD 0x6)."""

    action_uid: ClassVar[str] = ActionUID.QUERY_ACTUATOR_MEASUREMENT

    channel: int = 0x1E
    """I/O field: 0x00–0x1D=specific channel, 0x1E=all channels, 0x1F=input channel."""

    query_power: bool = False
    """qu field: False=query energy, True=query power."""
