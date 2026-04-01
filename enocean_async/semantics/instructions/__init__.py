from ..instructable import Instructable
from ..instruction import Instruction
from .cover import (
    CoverClose,
    CoverOpen,
    CoverQueryPositionAndAngle,
    CoverSetPositionAndAngle,
    CoverStop,
)
from .dimmer import Dim, Switch
from .fan import SetFanSpeed
from .switch import QueryActuatorMeasurement, QueryActuatorStatus, SetSwitchOutput
from .teach_in import TeachIn

INSTRUCTION_FOR: dict[Instructable, type[Instruction]] = {
    cls.action: cls
    for cls in [
        CoverClose,
        CoverOpen,
        CoverQueryPositionAndAngle,
        CoverSetPositionAndAngle,
        CoverStop,
        Dim,
        Switch,
        SetFanSpeed,
        QueryActuatorMeasurement,
        QueryActuatorStatus,
        SetSwitchOutput,
        TeachIn,
    ]
}
"""Maps each ``Instructable`` constant to its ``Instruction`` subclass.

Use this to construct a default (no-arg) instruction from an instructable, or to
introspect which instructions the library supports without hardcoding the mapping
in an integration.
"""

__all__ = [
    "Instructable",
    "Instruction",
    "INSTRUCTION_FOR",
    "CoverClose",
    "CoverOpen",
    "CoverQueryPositionAndAngle",
    "CoverSetPositionAndAngle",
    "CoverStop",
    "Dim",
    "Switch",
    "SetFanSpeed",
    "QueryActuatorMeasurement",
    "QueryActuatorStatus",
    "SetSwitchOutput",
    "TeachIn",
]
