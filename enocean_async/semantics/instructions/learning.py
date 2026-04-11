"""Gateway learning-mode control instruction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from ..instructable import Instructable
from ..instruction import Instruction

if TYPE_CHECKING:
    from ...address import EURID


@dataclass
class LearningToggle(Instruction):
    """Toggle gateway learning mode on/off.

    When issued while learning is inactive, starts a new session using
    the gateway's ``learning_timeout`` config value as the timeout and
    ``learning_sender`` config value to select the sender slot.
    When issued while learning is active, stops the session immediately.

    When ``for_device`` is set, the gateway enters focused learning mode:
    only teach-in telegrams from that specific EURID are accepted during
    the learning window.
    """

    action: ClassVar[Instructable] = Instructable.LEARNING_TOGGLE

    for_device: EURID | None = field(default=None, kw_only=True)
    """If set, only accept teach-in from this EURID during the learning window."""
