"""Tests for CoverObserver.

Covers:
- POSITION StateChange emitted on every message with a position entity
- ANGLE StateChange emitted when angle entity is present
- _derive_cover_state: open (pos=0), closed (pos=100), opening, closing,
  stopped (no change), None on first message at mid-position
- Watchdog timer fires "stopped" after COVER_WATCHDOG_TIMEOUT seconds when
  the cover is moving (opening/closing)
- Watchdog is cancelled when a new message arrives
- Messages from a different sender are ignored (inherited from Capability)
- message_type.id must be 4; other IDs are silently ignored
"""

import asyncio

from enocean_async.address import EURID
from enocean_async.eep.message import EEPMessage, EEPMessageType, ValueWithContext
from enocean_async.semantics.observable import Observable
from enocean_async.semantics.observation import ObservationSource
from enocean_async.semantics.observers.cover import (
    COVER_WATCHDOG_TIMEOUT,
    CoverObserver,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _eurid(s: str = "01:23:45:67") -> EURID:
    return EURID(s)


def _make_msg(
    sender: EURID,
    position: int | None = None,
    angle: int | None = None,
    message_type_id: int = 4,  # D2-05-00 reply
) -> EEPMessage:
    """Build a minimal EEPMessage suitable for CoverObserver.decode()."""
    entities: dict = {}
    if position is not None:
        entities[Observable.POSITION] = ValueWithContext(value=position, unit="%")
    if angle is not None:
        entities[Observable.ANGLE] = ValueWithContext(value=angle, unit="%")
    # CoverObserver only processes messages with message_type.id == 4.
    msg = EEPMessage(
        sender=sender,
        values=entities,
        decoded={
            "dummy": ValueWithContext(value=0)
        },  # non-empty so it passes the `if not scaled_values` guard
        message_type=EEPMessageType(id=message_type_id, description="reply"),
    )
    return msg


def _make_cap(device: EURID, received: list) -> CoverObserver:
    return CoverObserver(device_address=device, on_observation=received.append)


def _values_for(received: list, uid: Observable):
    return [sc.values[uid] for sc in received if uid in sc.values]


# ---------------------------------------------------------------------------
# Position and angle emission
# ---------------------------------------------------------------------------


class TestCoverCapabilityEmission:
    """Basic StateChange emission for POSITION and ANGLE."""

    async def test_position_state_change_emitted(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=50))
        await asyncio.sleep(0)
        assert any(Observable.POSITION in sc.values for sc in received)

    async def test_position_value_correct(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=75))
        await asyncio.sleep(0)
        pos_values = _values_for(received, Observable.POSITION)
        assert pos_values == [75]

    async def test_angle_state_change_emitted(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=50, angle=30))
        await asyncio.sleep(0)
        assert any(Observable.ANGLE in sc.values for sc in received)

    async def test_angle_value_correct(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=50, angle=45))
        await asyncio.sleep(0)
        ang_values = _values_for(received, Observable.ANGLE)
        assert ang_values == [45]

    async def test_no_angle_when_not_in_entities(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=50))  # no angle
        await asyncio.sleep(0)
        assert not any(Observable.ANGLE in sc.values for sc in received)

    async def test_position_source_is_telegram(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=50))
        await asyncio.sleep(0)
        pos_changes = [sc for sc in received if Observable.POSITION in sc.values]
        assert pos_changes[0].source == ObservationSource.TELEGRAM


# ---------------------------------------------------------------------------
# Cover state derivation
# ---------------------------------------------------------------------------


class TestCoverStateDerived:
    """_derive_cover_state encodes direction and boundary conditions."""

    async def test_position_zero_emits_open(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=0))
        await asyncio.sleep(0)
        cover_states = _values_for(received, Observable.COVER_STATE)
        assert "open" in cover_states

    async def test_position_100_emits_closed(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=100))
        await asyncio.sleep(0)
        cover_states = _values_for(received, Observable.COVER_STATE)
        assert "closed" in cover_states

    async def test_increasing_position_emits_closing(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=30))
        await asyncio.sleep(0)
        received.clear()
        cap.decode(_make_msg(device_address, position=50))
        await asyncio.sleep(0)
        cover_states = _values_for(received, Observable.COVER_STATE)
        assert "closing" in cover_states

    async def test_decreasing_position_emits_opening(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=70))
        await asyncio.sleep(0)
        received.clear()
        cap.decode(_make_msg(device_address, position=50))
        await asyncio.sleep(0)
        cover_states = _values_for(received, Observable.COVER_STATE)
        assert "opening" in cover_states

    async def test_no_cover_state_on_first_mid_position_message(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=50))
        await asyncio.sleep(0)
        cover_states = _values_for(received, Observable.COVER_STATE)
        assert "opening" not in cover_states
        assert "closing" not in cover_states

    async def test_unchanged_position_emits_stopped(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=50))
        await asyncio.sleep(0)
        received.clear()
        cap.decode(_make_msg(device_address, position=50))
        await asyncio.sleep(0)
        cover_states = _values_for(received, Observable.COVER_STATE)
        assert "stopped" in cover_states


# ---------------------------------------------------------------------------
# Watchdog timer
# ---------------------------------------------------------------------------


class TestCoverCapabilityWatchdog:
    """The async watchdog must fire "stopped" after COVER_WATCHDOG_TIMEOUT
    when the cover is moving, and be cancelled when a new update arrives."""

    async def test_watchdog_fires_stopped_after_timeout(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=20))
        cap.decode(_make_msg(device_address, position=40))
        await asyncio.sleep(COVER_WATCHDOG_TIMEOUT + 0.1)
        cover_states = _values_for(received, Observable.COVER_STATE)
        assert "stopped" in cover_states

    async def test_watchdog_source_is_timer(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=20))
        cap.decode(_make_msg(device_address, position=40))
        await asyncio.sleep(COVER_WATCHDOG_TIMEOUT + 0.1)
        timer_events = [
            sc
            for sc in received
            if Observable.COVER_STATE in sc.values
            and sc.source == ObservationSource.TIMER
        ]
        assert len(timer_events) >= 1

    async def test_new_message_cancels_watchdog(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        cap.decode(_make_msg(device_address, position=20))
        cap.decode(_make_msg(device_address, position=40))
        await asyncio.sleep(COVER_WATCHDOG_TIMEOUT * 0.3)
        cap.decode(_make_msg(device_address, position=60))
        await asyncio.sleep(COVER_WATCHDOG_TIMEOUT * 0.8)
        timer_stops = [
            sc
            for sc in received
            if Observable.COVER_STATE in sc.values
            and sc.source == ObservationSource.TIMER
        ]
        assert len(timer_stops) == 0


# ---------------------------------------------------------------------------
# Message filtering
# ---------------------------------------------------------------------------


class TestCoverCapabilityFiltering:
    """Messages from wrong sender or wrong message_type.id are ignored."""

    def test_ignores_message_from_other_sender(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        other = _eurid("AA:BB:CC:DD")
        cap.decode(_make_msg(other, position=50))
        assert len(received) == 0

    def test_ignores_message_with_wrong_type_id(self, device_address):
        received = []
        cap = _make_cap(device_address, received)
        msg = _make_msg(device_address, position=50, message_type_id=1)
        cap.decode(msg)
        assert len(received) == 0
