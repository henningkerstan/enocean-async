from dataclasses import dataclass

from enocean_async.eep.id import EEPID


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

    range_min: int | None = None
    """Minimum value of the data field's range."""

    range_max: int | None = None
    """Maximum value of the data field's range."""

    scale_min: float | None = None
    """Minimum value of the data field's scaled value."""

    scale_max: float | None = None
    """Maximum value of the data field's scaled value."""

    range_enum: dict[int, str] | None = None
    """Enumeration of possible values for the data field, if applicable."""

    unit: str | None = None
    """Unit of the data field, such as '°C' for temperature or '%' for humidity."""


@dataclass
class EEPTelegram:
    """An EEP telegram represents a specific type of message defined within an EEP, which may have its own structure and data fields."""

    name: str | None
    """Human-readable name for the telegram, describing its purpose or function."""

    datafields: list[EEPDataField]
    """List of data fields within the EEP."""


@dataclass
class EEP:
    """Base class for EEP data."""

    id: EEPID
    """Unique identifier for the EEP."""

    name: str
    """Human-readable name/description for the EEP."""

    cmd_size: int
    """Size of the telegram's command/message identifier in bits. If zero, there is only one telegram type."""

    cmd_offset: int | None
    """Bit offset of the telegram's command/message identifier within the EEP; either measured from left (if cmd_offset is non-negative) or from right (if cmd_offset is negative)."""

    telegrams: dict[int, EEPTelegram]
    """Dictionary of telegrams defined for this EEP, keyed by their command/message identifier, each with its own structure and data fields."""
