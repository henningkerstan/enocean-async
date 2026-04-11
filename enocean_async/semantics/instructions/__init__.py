from ..instructable import Instructable
from ..instruction import Instruction
from .central_command import CentralDim, CentralSwitch
from .cover import (
    CoverClose,
    CoverOpen,
    CoverQueryPositionAndAngle,
    CoverSetPositionAndAngle,
    CoverStop,
)
from .fan import SetFanSpeed
from .learn_telegram import LearnTelegram
from .learning import LearningToggle
from .switch import QueryActuatorMeasurement, QueryActuatorStatus, SetSwitchOutput

INSTRUCTION_FOR: dict[Instructable, type[Instruction]] = {
    cls.action: cls
    for cls in [
        CoverClose,
        CoverOpen,
        CoverQueryPositionAndAngle,
        CoverSetPositionAndAngle,
        CoverStop,
        CentralDim,
        CentralSwitch,
        SetFanSpeed,
        QueryActuatorMeasurement,
        QueryActuatorStatus,
        SetSwitchOutput,
        LearnTelegram,
        LearningToggle,
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
    "CentralDim",
    "CentralSwitch",
    "SetFanSpeed",
    "QueryActuatorMeasurement",
    "QueryActuatorStatus",
    "SetSwitchOutput",
    "LearnTelegram",
    "LearningToggle",
]
