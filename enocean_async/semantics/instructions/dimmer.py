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

    dim_value: float
    """Dimming value as a percentage: 0 = off, 100 = full brightness."""

    use_relative: bool = True
    """If True (default), encode as EDIMR=1 (relative, raw 0–100 maps directly).
    If False, encode as EDIMR=0 (absolute, raw 0–255 maps to 0–100 %)."""

    ramp_time: int | None = None
    """RMP field: ramping time in seconds (0 = immediately).
    None (default) → use device config ``"ramp_time"`` (defaults to 0 if not set)."""

    store: bool | None = None
    """STR field: True = store final value in device memory, False = do not store.
    None (default) → use device config ``"store"`` (defaults to False if not set)."""

    switch_on: bool = True
    """SW field: False = switch off, True = switch on."""
