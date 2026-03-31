from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import time
from typing import TYPE_CHECKING

from ..observable import Observable
from ..observation import Observation, ObservationSource
from ..observer_factory import ObserverFactory
from .observer import Observer

if TYPE_CHECKING:
    from ...eep.message import EEPMessage

# Watchdog timeout in seconds to detect when cover movement has stopped
COVER_WATCHDOG_TIMEOUT = 1.5


@dataclass
class CoverObserver(Observer):
    """Observer that emits position and angle updates for blinds/cover devices."""

    message_type_id: int = 4
    """Message type ID to listen to (4 for D2-05-00 'Reply position and angle',
    7 for A5-38-08 CMD=7 incoming status)."""

    _previous_position: int | None = field(default=None, init=False, repr=False)
    """Track previous position to derive cover state from movement."""

    _current_cover_state: str | None = field(default=None, init=False, repr=False)
    """Track the current cover state to avoid redundant state change emissions."""

    _watchdog_handle: asyncio.TimerHandle | None = field(
        default=None, init=False, repr=False
    )
    """Watchdog timer handle to detect when cover movement has stopped."""

    _stopped: bool = field(default=False, init=False, repr=False)
    """Set to True by stop() to prevent watchdog callbacks from firing after teardown."""

    def _decode_impl(self, message: EEPMessage) -> None:
        if not message.decoded:
            return

        if (
            message.message_type is None
            or message.message_type.id != self.message_type_id
        ):
            return

        current_time = time()

        pos_entity = message.values.get(Observable.POSITION)
        ang_entity = message.values.get(Observable.ANGLE)

        pos_value = pos_entity.value if pos_entity else None
        ang_value = ang_entity.value if ang_entity else None

        values: dict = {}

        if pos_value is not None:
            values[Observable.POSITION] = pos_value

            # Derive cover state from position changes
            cover_state = self._derive_cover_state(pos_value)
            if cover_state is not None:
                values[Observable.COVER_STATE] = cover_state
                self._current_cover_state = cover_state

                # Restart watchdog timer if cover is moving
                if cover_state in ("opening", "closing"):
                    self._restart_watchdog()

                if cover_state == "stopped":
                    if self._watchdog_handle is not None:
                        self._watchdog_handle.cancel()
                        self._watchdog_handle = None
            self._previous_position = pos_value

        if ang_value is not None:
            values[Observable.ANGLE] = ang_value

        if values:
            self._emit(
                Observation(
                    device=self.device_address,
                    entity="cover",
                    values=values,
                    timestamp=current_time,
                    source=ObservationSource.TELEGRAM,
                )
            )

    def _restart_watchdog(self) -> None:
        """Cancel existing watchdog and schedule a new one."""
        if self._watchdog_handle is not None:
            self._watchdog_handle.cancel()
        self._watchdog_handle = asyncio.get_running_loop().call_later(
            COVER_WATCHDOG_TIMEOUT, self._on_watchdog_timeout
        )

    def _on_watchdog_timeout(self) -> None:
        """Called when the watchdog fires; emits stopped state."""
        self._watchdog_handle = None
        if self._stopped:
            return
        self._current_cover_state = "stopped"
        self._emit(
            Observation(
                device=self.device_address,
                entity="cover",
                values={Observable.COVER_STATE: "stopped"},
                timestamp=time(),
                source=ObservationSource.TIMER,
            )
        )

    def stop(self) -> None:
        """Cancel the watchdog timer and prevent any further callbacks."""
        self._stopped = True
        if self._watchdog_handle is not None:
            self._watchdog_handle.cancel()
            self._watchdog_handle = None

    def _derive_cover_state(self, current_pos: int) -> str | None:
        """Derive cover state from current position and previous position."""

        if current_pos == 0:
            return "open"
        elif current_pos == 100:
            return "closed"

        if self._previous_position is None:
            # First message, determine state from absolute position
            return None  # Unknown state until we see a change, or we can infer from absolute position

        # Position changed, determine direction of movement
        if current_pos > self._previous_position:
            return "closing"
        elif current_pos < self._previous_position:
            return "opening"
        else:
            return "stopped"  # No change in position, state remains the same


def cover_factory(message_type_id: int = 4) -> ObserverFactory:
    """Return an ``ObserverFactory`` that creates a ``CoverObserver``.

    Args:
        message_type_id: Message type to listen to.  Use ``4`` for D2-05-00
            (``Reply position and angle``) and ``7`` for A5-38-08 CMD=7 status.
    """
    return ObserverFactory(
        factory=lambda addr, cb: CoverObserver(
            device_address=addr, on_observation=cb, message_type_id=message_type_id
        ),
    )
