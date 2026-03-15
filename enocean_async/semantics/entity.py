"""Entity model: physical sub-units of a device and their functional type classification."""

from dataclasses import dataclass, field
from enum import StrEnum

from .instructable import Instructable
from .observable import Observable
from .value_kind import ValueKind


class EntityType(StrEnum):
    """The physical/functional type of a device entity.

    Describes what kind of real-world thing the entity represents, using
    library-semantic names independent of any integration platform vocabulary.
    An integration maps these to its own platform concepts (e.g. HA maps
    ``PUSH_BUTTON`` → ``event`` platform, ``BINARY`` → ``binary_sensor``).

    Computed from an entity's ``observables`` and ``actions`` via
    ``Entity.entity_type``.  No separate declaration needed in EEP files.
    """

    SENSOR = "sensor"  # read-only continuous scalar (temperature, illumination, …)
    BINARY = "binary"  # read-only two-state (motion, contact, switch status, …)
    SWITCH = "switch"  # controllable on/off relay
    COVER = "cover"  # position-controllable cover / blind
    PUSH_BUTTON = "push_button"  # multi-value button events (a0, b1, ab0, …)
    DIMMER = "dimmer"  # controllable dimmer / PWM output
    FAN = "fan"  # fan speed control
    METADATA = "metadata"  # infrastructure: rssi, last_seen, telegram_count


_METADATA_OBSERVABLES = frozenset(
    {Observable.RSSI, Observable.LAST_SEEN, Observable.TELEGRAM_COUNT}
)
_COVER_INSTRUCTABLES = frozenset(
    {
        Instructable.COVER_SET_POSITION,
        Instructable.COVER_STOP,
        Instructable.COVER_OPEN,
        Instructable.COVER_CLOSE,
        Instructable.COVER_QUERY_POSITION,
    }
)


@dataclass(frozen=True)
class Entity:
    """A physical real-world sub-unit of a device (push button, relay channel, cover motor, sensor).

    Declared statically in the EEP specification. Each entity has a stable string ``id``
    within the device, a set of ``observables`` it reports, and a set of ``actions`` it accepts.
    A unique physical thing in the system is the pair ``(device_address, entity_id)``.
    """

    id: str
    observables: frozenset[Observable]
    actions: frozenset[Instructable] = field(default_factory=frozenset)

    @property
    def entity_type(self) -> EntityType:
        """Classify this entity's functional type from its observables and actions.

        The classification priority (first match wins):
        1. Instructable-driven actuator types (dimmer, fan, switch, cover).
        2. Push button (identified by Observable.PUSH_BUTTON).
        3. Metadata (rssi, last_seen, telegram_count).
        4. Binary sensor (any BINARY-kind observable).
        5. Sensor (default — scalar or enum read-only).
        """
        obs, act = self.observables, self.actions
        if Instructable.DIM in act:
            return EntityType.DIMMER
        if Instructable.SET_FAN_SPEED in act:
            return EntityType.FAN
        if Instructable.SET_SWITCH_OUTPUT in act:
            return EntityType.SWITCH
        if act & _COVER_INSTRUCTABLES:
            return EntityType.COVER
        if Observable.PUSH_BUTTON in obs:
            return EntityType.PUSH_BUTTON
        if obs <= _METADATA_OBSERVABLES:
            return EntityType.METADATA
        if any(o.kind == ValueKind.BINARY for o in obs):
            return EntityType.BINARY
        return EntityType.SENSOR
