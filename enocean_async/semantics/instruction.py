"""Base class for typed device instructions on the send pipeline."""

from dataclasses import dataclass, field
from typing import ClassVar

from .instructable import Instructable


@dataclass
class Instruction:
    """Base class for all typed device instructions.

    Subclasses must set ``action`` to the ``Instructable`` constant they represent,
    plus declare typed fields for every parameter the instruction requires.
    The corresponding EEP encoder receives the Instruction instance directly and translates
    its typed fields into raw EEP field values.
    """

    action: ClassVar[Instructable]
    """The Instructable constant this instruction represents. Must be set by each subclass."""

    entity_id: str = field(default="", kw_only=True)
    """Target entity ID. Encoders use this to determine the target channel or sub-unit."""
