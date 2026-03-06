"""Typed commands for cover / blind control (D2-05-00)."""

from dataclasses import dataclass
from typing import ClassVar

from ..instructable import Instructable
from ..instruction import Instruction


@dataclass
class SetCoverPosition(Instruction):
    """Move a cover to a specific vertical position and rotation angle.

    Both ``position`` and ``angle`` are raw EEP values (0–127, where 127 = 100%).
    """

    action: ClassVar[Instructable] = Instructable.SET_COVER_POSITION

    position: int
    """Vertical position: 0–127 (maps to 0–100 %)."""

    angle: int = 0
    """Rotation angle: 0–127 (maps to 0–100 %)."""

    repositioning_mode: int = 0
    """REPO field: 0 = directly to target, 1 = up first, 2 = down first."""

    lock_mode: int = 0
    """LOCK field: 0 = no change, 1 = set blockage, 2 = set alarm, 7 = unblock."""


@dataclass
class StopCover(Instruction):
    """Stop cover movement immediately."""

    action: ClassVar[Instructable] = Instructable.STOP_COVER


@dataclass
class QueryCoverPosition(Instruction):
    """Request the current position and angle from a cover actuator."""

    action: ClassVar[Instructable] = Instructable.QUERY_COVER_POSITION
