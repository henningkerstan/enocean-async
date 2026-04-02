"""Gateway learning-mode control instruction."""

from dataclasses import dataclass
from typing import ClassVar

from ..instructable import Instructable
from ..instruction import Instruction


@dataclass
class ToggleLearning(Instruction):
    """Toggle gateway learning mode on/off.

    When issued while learning is inactive, starts a new session using
    the gateway's ``learning_timeout`` config value as the timeout and
    ``learning_sender`` config value to select the sender slot.
    When issued while learning is active, stops the session immediately.
    """

    action: ClassVar[Instructable] = Instructable.TOGGLE_LEARNING
