"""Typed commands for A5-38-08 central command — lighting control."""

from dataclasses import dataclass
from typing import ClassVar

from ..instructable import Instructable
from ..instruction import Instruction


@dataclass
class Switch(Instruction):
    """Switch a device on or off, with optional timed and lock control."""

    action: ClassVar[Instructable] = Instructable.SWITCH

    switch_on: bool
    """SW field: True = switch on, False = switch off."""

    time: int = 0
    """TIM field: 0 = no timer, 1–65535 = time in 0.1 s steps (up to ~6553 s)."""

    lock: bool = False
    """LCK field: True = lock for duration (or indefinitely if time=0)."""

    delay: bool = False
    """DEL field: False = duration mode (switch now, revert after time);
    True = delay mode (switch after delay given by time)."""


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
