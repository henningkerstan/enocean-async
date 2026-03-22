"""Entity model: physical sub-units of a device and their functional type classification."""

from dataclasses import dataclass, field
from enum import StrEnum

from .instructable import Instructable
from .observable import Observable
from .value_kind import ValueKind


class EntityCategory(StrEnum):
    """Entity categorization for UI/UX purposes. Does not affect semantics or EEP code generation."""

    DEFAULT = "default"
    """Default — main device entities (light, cover, fan, switch, sensor)."""

    CONFIG = "config"
    """Setup-time configuration; shown under device settings (dimming mode, brightness limits)."""

    DIAGNOSTIC = "diagnostic"
    """Infrastructure / diagnostic info; shown under device diagnostics (rssi, last_seen)."""


class EntityType(StrEnum):
    """The physical/functional type of a device entity.

    Describes what kind of real-world thing the entity represents, using
    library-semantic names. Computed from an entity's ``observables``, ``actions``,
    and ``option_spec`` via ``Entity.entity_type``. No separate declaration needed
    in EEP files.
    """

    SENSOR = "sensor"  # read-only continuous scalar (temperature, illumination, …)
    BINARY = "binary"  # read-only two-state (motion, contact, switch status, …)
    SWITCH = "switch"  # controllable on/off relay
    COVER = "cover"  # position-controllable cover / blind
    BUTTON = "button"  # inbound: multi-value physical button events (a0, b1, ab0, …)
    DIMMER = "dimmer"  # controllable dimmer / PWM output
    FAN = "fan"  # fan speed control
    TRIGGER = "trigger"  # outbound: one-shot command / query trigger
    OPTION_ENUM = "option_enum"  # integration-local enum config — ``option_spec`` is ``EnumOptions``
    OPTION_NUMBER = "option_number"  # integration-local numeric config — ``option_spec`` is ``NumberRange``
    METADATA = "metadata"  # infrastructure: rssi, last_seen, telegram_count


@dataclass(frozen=True)
class EnumOptions:
    """Valid string choices for an ``OPTION_ENUM`` entity.

    Example::

        EnumOptions(options=("relative", "absolute"))
    """

    options: tuple[str, ...]


@dataclass(frozen=True)
class NumberRange:
    """Numeric range specification for an ``OPTION_NUMBER`` entity.

    Example::

        NumberRange(min_value=0.0, max_value=100.0, step=1.0, unit="%")
    """

    min_value: float
    max_value: float
    step: float = 1.0
    unit: str | None = None


_METADATA_OBSERVABLES = frozenset(
    {Observable.RSSI, Observable.LAST_SEEN, Observable.TELEGRAM_COUNT}
)
# Cover *control* instructables — excludes COVER_QUERY_POSITION_AND_ANGLE (a trigger/query).
_COVER_CONTROL_INSTRUCTABLES = frozenset(
    {
        Instructable.COVER_SET_POSITION_AND_ANGLE,
        Instructable.COVER_STOP,
        Instructable.COVER_OPEN,
        Instructable.COVER_CLOSE,
    }
)


@dataclass(frozen=True)
class Entity:
    """A physical real-world sub-unit of a device (button, relay channel, cover motor, sensor).

    Declared statically in the EEP specification. Each entity has a stable string ``id``
    within the device, a set of ``observables`` it reports, and a set of ``actions`` it accepts.
    A unique physical thing in the system is the pair ``(eurid, entity_id)``.

    **Config / auxiliary entities** use ``option_spec``:

    * ``EnumOptions(options=(...))`` — produces ``EntityType.OPTION_ENUM``
    * ``NumberRange(min, max, step, unit)`` — produces ``EntityType.OPTION_NUMBER``

    Set ``category`` to ``EntityCategory.CONFIG`` or ``EntityCategory.DIAGNOSTIC`` as appropriate.
    """

    id: str
    observables: frozenset[Observable] = field(default_factory=frozenset)
    actions: frozenset[Instructable] = field(default_factory=frozenset)
    option_spec: EnumOptions | NumberRange | None = None
    category: EntityCategory = EntityCategory.DEFAULT

    @property
    def entity_type(self) -> EntityType:
        """Classify this entity's functional type from its observables, actions, and option_spec.

        Classification priority (first match wins):

        1. Actuator types driven by specific Instructables (DIMMER, FAN, SWITCH, COVER).
        2. Physical button event (identified by ``Observable.BUTTON_EVENT``).
        3. ``OPTION_ENUM`` — ``option_spec`` is an ``EnumOptions`` instance.
        4. ``OPTION_NUMBER`` — ``option_spec`` is a ``NumberRange`` instance.
        5. ``TRIGGER`` — entity has outbound actions but no observables.
        6. Metadata sensors (rssi, last_seen, telegram_count).
        7. Binary sensor (any BINARY-kind observable).
        8. ``SENSOR`` — default.
        """
        obs, act = self.observables, self.actions
        if Instructable.DIM in act:
            return EntityType.DIMMER
        if Instructable.SET_FAN_SPEED in act:
            return EntityType.FAN
        if Instructable.SET_SWITCH_OUTPUT in act:
            return EntityType.SWITCH
        if act & _COVER_CONTROL_INSTRUCTABLES:
            return EntityType.COVER
        if Observable.BUTTON_EVENT in obs:
            return EntityType.BUTTON
        if isinstance(self.option_spec, EnumOptions):
            return EntityType.OPTION_ENUM
        if isinstance(self.option_spec, NumberRange):
            return EntityType.OPTION_NUMBER
        if act and not obs:
            return EntityType.TRIGGER
        if obs <= _METADATA_OBSERVABLES:
            return EntityType.METADATA
        if any(o.kind == ValueKind.BINARY for o in obs):
            return EntityType.BINARY
        return EntityType.SENSOR
