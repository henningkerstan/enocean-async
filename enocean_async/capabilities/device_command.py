"""Command sent to a device over the action pipeline."""

from dataclasses import dataclass, field


@dataclass
class DeviceCommand:
    """A command sent to an EnOcean device."""

    action: str
    """The action UID (ActionUID constant) identifying which command to send."""

    values: dict[str, int] = field(default_factory=dict)
    """Raw field values: mapping of EEP field_id → raw integer value."""
