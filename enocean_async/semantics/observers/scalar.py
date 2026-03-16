"""Generic scalar observer driven by observable annotation on EEP fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import TYPE_CHECKING

from ..observable import Observable
from ..observation import Observation, ObservationSource
from ..observer_factory import ObserverFactory
from .observer import Observer

if TYPE_CHECKING:
    from ...eep.message import EEPMessage


@dataclass
class ScalarObserver(Observer):
    """Generic observer that emits an Observation for any EEP field annotated with a matching observable.

    This observer reads from the EEP-level observable key that was propagated into EEPMessage.entities by EEPHandler.
    This makes it fully EEP-agnostic.
    """

    observable: Observable = field(kw_only=True)
    """The observable type to read from EEPMessage.entities and emit as an Observation."""

    entity_id: str = field(default="", kw_only=True)
    """Entity ID for the emitted Observation. Defaults to observable.value when empty."""

    entity_id_field: str | None = field(default=None, kw_only=True)
    """If set, read this field ID from message.values to derive entity_id dynamically."""

    entity_id_not_applicable: int | None = field(default=None, kw_only=True)
    """Raw entity_id_field value that means 'not channel-specific'; falls back to entity_id."""

    entity_id_prefix: str = field(default="", kw_only=True)
    """Prefix prepended to the field value when building entity_id from entity_id_field (e.g. ``"ch"``)."""

    entity_id_offset: int = field(default=0, kw_only=True)
    """Integer added to the raw field value when building entity_id from entity_id_field (e.g. ``1`` to produce ``"ch1"`` from raw=0)."""

    entity_id_suffix: str = field(default="", kw_only=True)
    """Suffix appended when building entity_id from entity_id_field (e.g. ``"_switch_state"`` → ``"ch1_switch_state"``)."""

    def _resolve_entity_id(self, message: EEPMessage) -> str:
        """Determine the entity_id for this state change."""
        if self.entity_id_field is not None:
            raw = message.raw.get(self.entity_id_field)
            if raw is not None and raw != self.entity_id_not_applicable:
                return f"{self.entity_id_prefix}{raw + self.entity_id_offset}{self.entity_id_suffix}"
        return self.entity_id or self.observable.value

    def _decode_impl(self, message: EEPMessage) -> None:
        v = message.values.get(self.observable)
        if v is None or v.value is None:
            return

        self._emit(
            Observation(
                device=self.device_address,
                entity=self._resolve_entity_id(message),
                values={self.observable: v.value},
                timestamp=time(),
                source=ObservationSource.TELEGRAM,
            )
        )


def scalar_factory(
    observable: Observable,
    *,
    entity_id: str = "",
    entity_id_field: str | None = None,
    entity_id_not_applicable: int | None = None,
    entity_id_prefix: str = "",
    entity_id_offset: int = 0,
    entity_id_suffix: str = "",
) -> ObserverFactory:
    """Return an ``ObserverFactory`` that creates a ``ScalarObserver`` for ``observable``.

    Args:
        observable: The observable this observer reads and emits.
        entity_id: Static entity ID for the Observation (defaults to observable.value).
            Also used as fallback when entity_id_field resolves to entity_id_not_applicable.
        entity_id_field: Optional field ID to read the entity ID from (e.g. ``"I/O"`` for D2-01).
        entity_id_not_applicable: Raw field value meaning "not channel-specific"; falls back to entity_id.
        entity_id_prefix: Prefix prepended to the field value (e.g. ``"ch"`` → ``"ch1"``).
        entity_id_offset: Offset added to the raw field value (e.g. ``1`` to produce ``"ch1"`` from raw=0).
        entity_id_suffix: Suffix appended to the derived id (e.g. ``"_switch_state"`` → ``"ch1_switch_state"``).
    """
    return ObserverFactory(
        factory=lambda addr, cb: ScalarObserver(
            device_address=addr,
            on_observation=cb,
            observable=observable,
            entity_id=entity_id,
            entity_id_field=entity_id_field,
            entity_id_not_applicable=entity_id_not_applicable,
            entity_id_prefix=entity_id_prefix,
            entity_id_offset=entity_id_offset,
            entity_id_suffix=entity_id_suffix,
        ),
    )
