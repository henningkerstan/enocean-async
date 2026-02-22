from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from enocean_async.eep.id import EEPID

type TelegramRawValues = dict[str, int]
type ScaleFunction = Callable[[TelegramRawValues], float]
type UnitFunction = Callable[[TelegramRawValues], str]


@dataclass
class EEPDataField:
    """An EEP data field represents a single data point within an EEP, such as a sensor value or a control command."""

    id: str
    """Unique identifier for the data field, typically a short string like 'R1', 'POS' etc."""

    name: str
    """Human-readable name for the data field, providing a descriptive label."""

    offset: int
    """Bit offset of the data field within the EEP."""

    size: int
    """Size of the data field in bits."""

    range_min: int = 0
    """Minimum value of the data field's range."""

    range_max: int | None = None
    """Maximum value of the data field's range, defaulting to the maximum representable by the given size in bits (e.g. 2^size - 1)."""

    scale_min_fn: ScaleFunction = lambda _: 0.0
    """Function to compute scale_min based on message values. Defaults to constant 0.0."""

    scale_max_fn: ScaleFunction | None = None
    """Function to compute scale_max based on message values. Defaults to constant 0.0."""

    unit_fn: UnitFunction = lambda _: ""
    """Function to compute unit based on message values. Defaults to empty string."""

    range_enum: dict[int, str] | None = None
    """Enumeration of possible values for the data field, if applicable."""

    __range_max_backing: int | None = field(init=False, default=None, repr=False)
    """Private backing field for range_max property with validation."""

    def __post_init__(self):
        if self.range_enum:
            # If an enumeration is provided, range_min and range_max should be derived from the enum keys
            enum_keys = self.range_enum.keys()
            self.range_min = min(enum_keys)
            # Use setter for validation
            self.range_max = max(enum_keys)
        else:
            # If no enumeration, ensure range_max is set based on size if not provided
            if self.range_max is None or self.range_max > (1 << self.size) - 1:
                self.range_max = (1 << self.size) - 1

        if self.scale_max_fn is None:
            self.scale_max_fn = lambda _: float(self.range_max)


@dataclass
class EEPTelegram:
    """An EEP telegram represents a specific type of message defined within an EEP, which may have its own structure and data fields."""

    name: str | None
    """Human-readable name for the telegram, describing its purpose or function."""

    datafields: list[EEPDataField] = field(default_factory=list)
    """List of data fields within the telegram."""


@dataclass
class EEP:
    """Base class for EEP data."""

    id: EEPID
    """Unique identifier for the EEP."""

    name: str
    """Human-readable name/description for the EEP."""

    cmd_size: int = 0
    """Size of the telegram's command/message identifier in bits. If zero, there is only one telegram type."""

    cmd_offset: int | None = None
    """Bit offset of the telegram's command/message identifier within the EEP; either measured from left (if cmd_offset is non-negative) or from right (if cmd_offset is negative)."""

    telegrams: dict[int, EEPTelegram] = field(default_factory=dict)
    """Dictionary of telegrams defined for this EEP, keyed by their command/message identifier, each with its own structure and data fields."""


@dataclass
class SingleTelegramEEP(EEP):
    """EEP variant for profiles with a single telegram type (cmd_size=0, no telegram selector)."""

    def __init__(
        self,
        id: EEPID,
        name: str,
        datafields: list[EEPDataField],
    ):
        """Initialize a single-telegram EEP.

        Args:
            id: Unique identifier for the EEP.
            name: Human-readable name/description.
            datafields: List of data fields in this single telegram.
        """

        super().__init__(
            id=id,
            name=name,
            cmd_size=0,
            cmd_offset=None,
            telegrams={0: EEPTelegram(name=None, datafields=datafields)},
        )
