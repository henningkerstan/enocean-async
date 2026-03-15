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

    action: ClassVar[Instructable] = Instructable.COVER_SET_POSITION

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

    action: ClassVar[Instructable] = Instructable.COVER_QUERY_POSITION


@dataclass
class CoverOpen(Instruction):
    """Open the cover/shutter fully."""

    action: ClassVar[Instructable] = Instructable.COVER_OPEN


@dataclass
class CoverClose(Instruction):
    """Close the cover/shutter fully."""

    action: ClassVar[Instructable] = Instructable.COVER_CLOSE
