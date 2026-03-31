from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
from time import time
from typing import TYPE_CHECKING

_logger = logging.getLogger(__name__)

from ..observable import Observable
from ..observation import Observation, ObservationSource
from ..observer_factory import ObserverFactory
from .observer import Observer

if TYPE_CHECKING:
    from ...eep.message import EEPMessage

PRESSED = "pressed"
RELEASED = "released"
CLICKED = "clicked"
HELD = "held"


@dataclass
class ButtonObserver(Observer):
    """Base observer for button devices.

    Provides timing-based state machine behavior for:
    - pressed: Initial press event (fires immediately on button press)
    - clicked: Short press (fires upon release if duration < hold threshold)
    - held: Long press — emitted when hold threshold is exceeded while button is still pressed
    - released: Button released after a hold (fires on release telegram or after timeout)
    """

    _HOLD_THRESHOLD: float = 0.4
    """Time in seconds to consider a press as a "hold"."""

    _RELEASE_TIMEOUT: float = 30.0
    """Time in seconds after which a button is considered released, if no release telegram was received."""

    _last_pressed_timestamps: dict[str, float] = field(default_factory=dict)
    """Timestamp of the last press event (for each button ID)."""

    _button_was_held: dict[str, bool] = field(default_factory=dict)
    """Indicates whether the button was held (for each button ID)."""

    _hold_timers: dict[str, asyncio.TimerHandle] = field(default_factory=dict)
    """Hold timers for each button ID, to track when to emit `held` events (after hold threshold elapses)."""

    _release_timers: dict[str, asyncio.TimerHandle] = field(default_factory=dict)
    """Release timers for each button ID, to track when to emit `released` events (timeout)."""

    def _emit_held(self, button_id: str) -> None:
        """Emit held event (called by hold timer)."""
        if button_id not in self._last_pressed_timestamps:
            return

        self._button_was_held[button_id] = True

        self._emit(
            Observation(
                device=self.device_address,
                entity=button_id,
                values={Observable.BUTTON_EVENT: HELD},
                timestamp=time(),
                source=ObservationSource.TIMER,
            )
        )

    def _emit_released(self, button_id: str) -> None:
        """Emit released event (called by release-timeout timer)."""
        if button_id not in self._last_pressed_timestamps:
            return

        if button_id in self._hold_timers:
            self._hold_timers[button_id].cancel()
            del self._hold_timers[button_id]

        self._emit(
            Observation(
                device=self.device_address,
                entity=button_id,
                values={Observable.BUTTON_EVENT: RELEASED},
                timestamp=time(),
                source=ObservationSource.TIMER,
            )
        )

        if button_id in self._release_timers:
            del self._release_timers[button_id]

    def _button_pressed(
        self, button_id: str, current_time: float | None = None
    ) -> None:
        """Handle a button press."""
        if current_time is None:
            current_time = time()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            _logger.error("Cannot schedule button timers: no running event loop.")
            return

        # if button was held, emit a `released` event before emitting the new `pressed` event;
        # this can only happen if the release telegram got lost
        if self._button_was_held.get(button_id, False):
            self._emit(
                Observation(
                    device=self.device_address,
                    entity=button_id,
                    values={Observable.BUTTON_EVENT: RELEASED},
                    timestamp=current_time,
                    source=ObservationSource.TELEGRAM,
                )
            )

        # emit pressed event
        self._emit(
            Observation(
                device=self.device_address,
                entity=button_id,
                values={Observable.BUTTON_EVENT: PRESSED},
                timestamp=current_time,
                source=ObservationSource.TELEGRAM,
            )
        )

        # store press time and reset held state
        self._last_pressed_timestamps[button_id] = current_time
        self._button_was_held[button_id] = False

        # restart hold timer
        if button_id in self._hold_timers:
            self._hold_timers[button_id].cancel()
        self._hold_timers[button_id] = loop.call_later(
            self._HOLD_THRESHOLD, self._emit_held, button_id
        )

        # restart release timeout timer
        if button_id in self._release_timers:
            self._release_timers[button_id].cancel()
        self._release_timers[button_id] = loop.call_later(
            self._RELEASE_TIMEOUT, self._emit_released, button_id
        )

    def _button_released(self, button_id: str, current_time: float) -> None:
        """Handle a button release."""
        press_time = self._last_pressed_timestamps.get(button_id)
        if press_time is None:
            return  # release without prior press — ignore

        press_duration = current_time - press_time

        if button_id in self._hold_timers:
            self._hold_timers[button_id].cancel()
            del self._hold_timers[button_id]

        if button_id in self._release_timers:
            self._release_timers[button_id].cancel()
            del self._release_timers[button_id]

        was_held = self._button_was_held.get(button_id, False)

        if was_held:
            self._emit(
                Observation(
                    device=self.device_address,
                    entity=button_id,
                    values={Observable.BUTTON_EVENT: RELEASED},
                    timestamp=current_time,
                    source=ObservationSource.TELEGRAM,
                )
            )
        elif press_duration < self._HOLD_THRESHOLD:
            self._emit(
                Observation(
                    device=self.device_address,
                    entity=button_id,
                    values={Observable.BUTTON_EVENT: CLICKED},
                    timestamp=current_time,
                    source=ObservationSource.TELEGRAM,
                )
            )

        del self._last_pressed_timestamps[button_id]
        if button_id in self._button_was_held:
            del self._button_was_held[button_id]

    def stop(self) -> None:
        """Cancel all pending hold and release timers."""
        for handle in self._hold_timers.values():
            handle.cancel()
        self._hold_timers.clear()
        for handle in self._release_timers.values():
            handle.cancel()
        self._release_timers.clear()

    def _decode_impl(self, message: EEPMessage) -> None:
        """Decode button messages into semantic state changes with timing."""
        raise NotImplementedError("Subclasses must implement the _decode_impl method.")


@dataclass
class F6_02_01_02_ButtonObserver(ButtonObserver):
    """Button observer for F6-02-01/02 rocker switches.

    Handles R1/EB/R2/SA fields from F6-02-01 and F6-02-02 telegrams.
    """

    def _decode_impl(self, message: EEPMessage) -> None:
        if not {"R1", "EB", "R2", "SA"}.issubset(message.decoded):
            return

        r1 = message.decoded["R1"].value
        eb = message.decoded["EB"].value
        sa = message.decoded["SA"].value
        r2 = message.decoded["R2"].value

        current_time = time()

        if eb == "pressed" and r1 is not None:
            self._button_pressed(button_id=r1, current_time=current_time)
            if sa == "2nd action valid" and r2 is not None and r2 != r1:
                self._button_pressed(button_id=r2, current_time=current_time)
        elif eb == "released":
            for button_id in list(self._last_pressed_timestamps.keys()):
                self._button_released(button_id=button_id, current_time=current_time)


#


def f6_button_factory() -> ObserverFactory:
    """Return an ``ObserverFactory`` that creates an ``F6_02_01_02_ButtonObserver``.

    Emits ``Observable.BUTTON_EVENT`` state changes with the button ID (``"a0"``, ``"b1"``, …)
    as ``Observation.entity`` and the event type (``"clicked"``, ``"held"``, ``"pressed"``,
    ``"released"``) as the value in ``values``. Simultaneous two-button presses fire two
    separate atomic events with the same timestamp.
    """
    return ObserverFactory(
        factory=lambda addr, cb: F6_02_01_02_ButtonObserver(
            device_address=addr, on_observation=cb
        ),
    )
