"""Typed commands for cover / blind / shutter control."""

from dataclasses import dataclass
from typing import ClassVar

from ..instructable import Instructable
from ..instruction import Instruction


@dataclass
class CoverSetPositionAndAngle(Instruction):
    """Move a cover to a specific vertical position and rotation angle.

    ``position`` and ``angle`` are in percent (0–100).
    Pass ``None`` to leave the current value unchanged.
    """

    action: ClassVar[Instructable] = Instructable.COVER_SET_POSITION_AND_ANGLE

    position: int | None = None
    """Vertical position in percent (0–100), or None to keep the current position."""

    angle: int | None = None
    """Rotation angle in percent (0–100), or None to keep the current angle."""

    repositioning_mode: int = 0
    """REPO field (D2-05-00 only): 0 = directly to target, 1 = up first, 2 = down first."""

    lock_mode: int = 0
    """LOCK field (D2-05-00 only): 0 = no change, 1 = set blockage, 2 = set alarm, 7 = unblock."""


@dataclass
class CoverStop(Instruction):
    """Stop cover movement immediately."""

    action: ClassVar[Instructable] = Instructable.COVER_STOP


@dataclass
class CoverQueryPositionAndAngle(Instruction):
    """Request the current position and angle from a cover actuator."""

    action: ClassVar[Instructable] = Instructable.COVER_QUERY_POSITION_AND_ANGLE


@dataclass
class CoverOpen(Instruction):
    """Open the cover/shutter fully."""

    action: ClassVar[Instructable] = Instructable.COVER_OPEN


@dataclass
class CoverClose(Instruction):
    """Close the cover/shutter fully."""

    action: ClassVar[Instructable] = Instructable.COVER_CLOSE


@dataclass
class CoverSetParameters(Instruction):
    """Configure the timing parameters of a D2-05 blind actuator (CMD 5 – Set Parameters).

    Only supported by D2-05 types 0x00 and 0x01.
    """

    action: ClassVar[Instructable] = Instructable.COVER_SET_PARAMETERS

    vertical_run_time_ms: int | None = None
    """Measured duration of a full vertical run, in ms (5000–300000). None = do not change."""

    rotation_time_ms: int | None = None
    """Measured duration of a full slat rotation, in ms (10–2540); 0 = no rotation. None = do not change."""

    alarm_action: int = 7
    """AA field: 0 = no action, 1 = immediate stop, 2 = go up (0%), 3 = go down (100%), 7 = no change (default)."""
