"""Typed commands for central command / dimmer control (A5-38-08)."""

from dataclasses import dataclass
from typing import ClassVar

from ..instructable import Instructable
from ..instruction import Instruction


@dataclass
class Dim(Instruction):
    """Dim a light to a specific value."""

    action: ClassVar[Instructable] = Instructable.DIM

    dim_value: int
    """Dimming value as a percentage: 0 = off, 100 = full brightness."""

    ramp_time: int = 0
    """RMP field: ramping time in seconds (0 = immediately)."""

    store: bool = False
    """STR field: False = do not store final value, True = store."""

    switch_on: bool = True
    """SW field: False = switch off, True = switch on."""
