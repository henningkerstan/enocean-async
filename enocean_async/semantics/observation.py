from dataclasses import dataclass, field
from enum import IntEnum
from time import time
from typing import Any, Callable

from ..address import SenderAddress
from .observable import Observable


class ObservationSource(IntEnum):
    """Origin of an ``Observation``.

    Distinguishes observations derived from a received telegram from those
    synthesised by an internal timer (e.g. a cover watchdog or button-release timeout).
    """

    TELEGRAM = 0
    """Observation was produced by a received ERP1 telegram."""

    TIMER = 1
    """Observation was produced by an internal timer (no telegram received)."""


@dataclass
class Observation:
    """A semantic update emitted by an observer for one entity.

    Each ``Observation`` carries a snapshot of one or more observable values for a
    single ``(device, entity)`` pair.  Updates are partial: ``values`` only contains
    the observables that were present in the triggering event.  For example, a D2-01
    measurement response carrying only ``POWER`` will produce an ``Observation`` with
    a single entry in ``values``; the caller must not infer anything about absent keys.

    The unit for any value is defined by ``Observable.unit`` and is not repeated here.
    """

    device: SenderAddress
    """Address of the device that produced this observation."""

    entity: str
    """Identifier for the logical entity within the device (e.g. ``"temperature"``, ``"a0"``).

    For single-entity devices this is the observable's string value (``observable.value``).
    For multi-channel devices (D2-01) or multi-button devices (F6-02) it encodes the
    channel or button ID (e.g. ``"3"``, ``"ab0"``).
    """

    values: dict[Observable, Any]
    """Observable values reported by this observation, keyed by ``Observable``.

    Only observables present in the triggering event are included.
    """

    timestamp: float = field(default_factory=time)
    """Wall-clock time of the observation as a Unix timestamp (seconds since epoch).

    Defaults to ``time.time()`` at construction.
    """

    source: ObservationSource = ObservationSource.TELEGRAM
    """Whether this observation was triggered by a telegram or an internal timer."""


type ObservationCallback = Callable[[Observation], None]
"""Callback type for receiving ``Observation`` events."""
