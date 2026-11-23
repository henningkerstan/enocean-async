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
    and ``config_spec`` via ``Entity.entity_type``. No separate declaration needed
    in EEP files.
    """

    SENSOR = "sensor"
    """Read-only continuous scalar (temperature, illumination, …)."""

    BINARY = "binary"
    """Read-only two-state value (motion, contact, switch status, …)."""

    SWITCH = "switch"
    """Controllable on/off relay."""

    COVER = "cover"
    """Position-controllable cover / blind."""

    BUTTON = "button"
    """Inbound: multi-value physical button events (a0, b1, …)."""

    DIMMER = "dimmer"
    """Controllable dimmer / PWM output."""

    FAN = "fan"
    """Fan speed control."""

    TRIGGER = "trigger"
    """Outbound: one-shot command / query trigger."""

    CONFIG_ENUM = "config_enum"
    """Integration-local enum config; ``config_spec`` is ``EnumOptions``."""

    CONFIG_NUMBER = "config_number"
    """Integration-local numeric config; ``config_spec`` is ``NumberRange``."""

    METADATA = "metadata"
    """Infrastructure: rssi, last_seen, telegram_count."""


@dataclass(frozen=True)
class EnumOptions:
    """Valid string choices for a ``CONFIG_ENUM`` entity.

    Example::

        EnumOptions(options=("relative", "absolute"))
    """

    options: tuple[str, ...]
    """The valid values, in the order they should be presented."""

    default: str | None = None
    """The value a device starts with, one of ``options``; ``None`` if there is no default."""


@dataclass(frozen=True)
class NumberRange:
    """Numeric range specification for a ``CONFIG_NUMBER`` entity.

    Example::

        NumberRange(min_value=0.0, max_value=100.0, step=1.0, unit="%")
    """

    min_value: float
    """Smallest valid value."""

    max_value: float
    """Largest valid value."""

    step: float = 1.0
    """Granularity of valid values, e.g. ``1.0`` for whole numbers."""

    unit: str | None = None
    """Unit of the value for display, e.g. ``"%"`` or ``"s"``; ``None`` if it has no unit."""

    default: float | None = None
    """The value a device starts with; ``None`` if there is no default."""


def BoolOption(default: bool = False) -> EnumOptions:
    """Shorthand for a two-state ``CONFIG_ENUM`` entity with ``"no"`` / ``"yes"`` options.

    Equivalent to ``EnumOptions(options=("no", "yes"), default="yes" if default else "no")``.

    Example::

        BoolOption()           # default "no"
        BoolOption(default=True)  # default "yes"
    """
    return EnumOptions(options=("no", "yes"), default="yes" if default else "no")


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
    A unique physical thing in the system is the pair ``(device address, entity_id)``.

    **Config / auxiliary entities** use ``config_spec``:

    * ``EnumOptions(options=(...))`` — produces ``EntityType.CONFIG_ENUM``
    * ``NumberRange(min, max, step, unit)`` — produces ``EntityType.CONFIG_NUMBER``

    Set ``category`` to ``EntityCategory.CONFIG`` or ``EntityCategory.DIAGNOSTIC`` as appropriate.
    """

    id: str
    """Stable identifier of the entity within its device, e.g. ``"temperature"``, ``"ch2_cover"`` or ``"a0"``.
    Together with the device address it identifies the entity in the system."""

    observables: frozenset[Observable] = field(default_factory=frozenset)
    """The quantities this entity reports, as keys of ``Observation.values``. Empty for entities which only accept actions."""

    actions: frozenset[Instructable] = field(default_factory=frozenset)
    """The actions this entity accepts via ``Gateway.send_command()``. Empty for read-only entities."""

    config_spec: EnumOptions | NumberRange | None = None
    """For a setting, i.e. a value the user chooses and the gateway keeps in the device's config
    (see ``Gateway.set_device_config()``): its valid values and default. ``None`` for entities
    which report values of the device or accept actions."""

    category: EntityCategory = EntityCategory.DEFAULT
    """Where an integration should present the entity: as a main entity, under settings or under diagnostics."""

    @property
    def entity_type(self) -> EntityType:
        """Classify this entity's functional type from its observables, actions, and config_spec.

        Classification priority (first match wins):

        1. Actuator types driven by specific Instructables (DIMMER, FAN, SWITCH, COVER).
        2. Physical button event (identified by ``Observable.BUTTON_EVENT``).
        3. ``CONFIG_ENUM`` — ``config_spec`` is an ``EnumOptions`` instance.
        4. ``CONFIG_NUMBER`` — ``config_spec`` is a ``NumberRange`` instance.
        5. ``TRIGGER`` — entity has outbound actions but no observables.
        6. Metadata sensors (rssi, last_seen, telegram_count).
        7. Binary sensor (any BINARY-kind observable).
        8. ``SENSOR`` — default.
        """
        obs, act = self.observables, self.actions
        if Instructable.CENTRAL_DIM in act:
            return EntityType.DIMMER
        if Instructable.SET_FAN_SPEED in act:
            return EntityType.FAN
        if Instructable.SET_SWITCH_OUTPUT in act:
            return EntityType.SWITCH
        if act & _COVER_CONTROL_INSTRUCTABLES:
            return EntityType.COVER
        if Observable.BUTTON_EVENT in obs:
            return EntityType.BUTTON
        if isinstance(self.config_spec, EnumOptions):
            return EntityType.CONFIG_ENUM
        if isinstance(self.config_spec, NumberRange):
            return EntityType.CONFIG_NUMBER
        if act and not obs:
            return EntityType.TRIGGER
        if obs <= _METADATA_OBSERVABLES:
            return EntityType.METADATA
        if any(o.kind == ValueKind.BINARY for o in obs):
            return EntityType.BINARY
        return EntityType.SENSOR
