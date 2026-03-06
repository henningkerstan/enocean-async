"""Typed commands for fan speed control (D2-20-02)."""

from dataclasses import dataclass
from typing import ClassVar

from ..instructable import Instructable
from ..instruction import Instruction


@dataclass
class SetFanSpeed(Instruction):
    """Set the fan speed of a controlled ventilation unit."""

    action: ClassVar[Instructable] = Instructable.SET_FAN_SPEED

    fan_speed: int
    """FS field: 0–100 = percentage, 253 = Auto, 254 = Default, 255 = No change."""

    room_size_reference: int = 3
    """RSR field: 0 = Used, 1 = Not used, 2 = Default, 3 = No change."""

    room_size: int = 15
    """RS field: 0–14 = size ranges, 15 = No change."""
