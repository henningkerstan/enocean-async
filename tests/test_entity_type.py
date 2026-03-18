"""Tests for ValueKind on Observable members and Entity.entity_type classification.

Covers:
ValueKind on Observable:
- SCALAR members carry ValueKind.SCALAR
- BINARY members carry ValueKind.BINARY
- ENUM members carry ValueKind.ENUM

Entity.entity_type:
- Instructable.DIM → DIMMER
- Instructable.SET_FAN_SPEED → FAN
- Instructable.SET_SWITCH_OUTPUT → SWITCH
- Cover instructables → COVER
- Observable.BUTTON_EVENT → BUTTON
- Metadata observables only → METADATA
- Any BINARY-kind observable, no actions → BINARY
- Scalar/enum observables, no actions → SENSOR
- Priority: instructables beat observable kind
"""

import pytest

from enocean_async.semantics.entity import Entity, EntityType
from enocean_async.semantics.instructable import Instructable
from enocean_async.semantics.observable import Observable
from enocean_async.semantics.value_kind import ValueKind

# ---------------------------------------------------------------------------
# ValueKind on Observable members
# ---------------------------------------------------------------------------


class TestObservableKind:
    """Every Observable member carries the correct ValueKind."""

    def test_temperature_is_scalar(self):
        assert Observable.TEMPERATURE.kind == ValueKind.SCALAR

    def test_humidity_is_scalar(self):
        assert Observable.HUMIDITY.kind == ValueKind.SCALAR

    def test_illumination_is_scalar(self):
        assert Observable.ILLUMINATION.kind == ValueKind.SCALAR

    def test_voltage_is_scalar(self):
        assert Observable.VOLTAGE.kind == ValueKind.SCALAR

    def test_power_is_scalar(self):
        assert Observable.POWER.kind == ValueKind.SCALAR

    def test_energy_is_scalar(self):
        assert Observable.ENERGY.kind == ValueKind.SCALAR

    def test_position_is_scalar(self):
        assert Observable.POSITION.kind == ValueKind.SCALAR

    def test_rssi_is_scalar(self):
        assert Observable.RSSI.kind == ValueKind.SCALAR

    def test_last_seen_is_scalar(self):
        assert Observable.LAST_SEEN.kind == ValueKind.SCALAR

    def test_telegram_count_is_scalar(self):
        assert Observable.TELEGRAM_COUNT.kind == ValueKind.SCALAR

    def test_motion_is_binary(self):
        assert Observable.MOTION.kind == ValueKind.BINARY

    def test_switch_state_is_binary(self):
        assert Observable.SWITCH_STATE.kind == ValueKind.BINARY

    def test_contact_state_is_binary(self):
        assert Observable.CONTACT_STATE.kind == ValueKind.BINARY

    def test_day_night_is_binary(self):
        assert Observable.DAY_NIGHT.kind == ValueKind.BINARY

    def test_occupancy_button_is_binary(self):
        assert Observable.OCCUPANCY_BUTTON.kind == ValueKind.BINARY

    def test_error_level_is_binary(self):
        assert Observable.ERROR_LEVEL.kind == ValueKind.BINARY

    def test_cover_state_is_enum(self):
        assert Observable.COVER_STATE.kind == ValueKind.ENUM

    def test_window_state_is_enum(self):
        assert Observable.WINDOW_STATE.kind == ValueKind.ENUM

    def test_button_event_is_enum(self):
        assert Observable.BUTTON_EVENT.kind == ValueKind.ENUM

    def test_pilot_wire_mode_is_enum(self):
        assert Observable.PILOT_WIRE_MODE.kind == ValueKind.ENUM


# ---------------------------------------------------------------------------
# Entity.entity_type — instructable-driven types
# ---------------------------------------------------------------------------


class TestEntityTypeActuators:
    """Instructable presence determines actuator entity type."""

    def test_dim_gives_dimmer(self):
        e = Entity(
            id="light", observables=frozenset(), actions=frozenset({Instructable.DIM})
        )
        assert e.entity_type == EntityType.DIMMER

    def test_set_fan_speed_gives_fan(self):
        e = Entity(
            id="fan",
            observables=frozenset(),
            actions=frozenset({Instructable.SET_FAN_SPEED}),
        )
        assert e.entity_type == EntityType.FAN

    def test_set_switch_output_gives_switch(self):
        e = Entity(
            id="relay",
            observables=frozenset({Observable.SWITCH_STATE}),
            actions=frozenset({Instructable.SET_SWITCH_OUTPUT}),
        )
        assert e.entity_type == EntityType.SWITCH

    def test_cover_instructables_give_cover(self):
        e = Entity(
            id="cover",
            observables=frozenset(
                {Observable.POSITION, Observable.ANGLE, Observable.COVER_STATE}
            ),
            actions=frozenset(
                {
                    Instructable.COVER_SET_POSITION,
                    Instructable.COVER_STOP,
                    Instructable.COVER_QUERY_POSITION,
                }
            ),
        )
        assert e.entity_type == EntityType.COVER

    def test_stop_cover_alone_gives_cover(self):
        # Any cover instructable triggers COVER, not just the full set.
        e = Entity(
            id="cover",
            observables=frozenset(),
            actions=frozenset({Instructable.COVER_STOP}),
        )
        assert e.entity_type == EntityType.COVER


# ---------------------------------------------------------------------------
# Entity.entity_type — observable-driven types
# ---------------------------------------------------------------------------


class TestEntityTypeObservables:
    """Observable identity and kind drive classification when no actions present."""

    def test_button_event_gives_button(self):
        e = Entity(id="a0", observables=frozenset({Observable.BUTTON_EVENT}))
        assert e.entity_type == EntityType.BUTTON

    def test_rssi_gives_metadata(self):
        e = Entity(id="rssi", observables=frozenset({Observable.RSSI}))
        assert e.entity_type == EntityType.METADATA

    def test_last_seen_gives_metadata(self):
        e = Entity(id="last_seen", observables=frozenset({Observable.LAST_SEEN}))
        assert e.entity_type == EntityType.METADATA

    def test_telegram_count_gives_metadata(self):
        e = Entity(
            id="telegram_count", observables=frozenset({Observable.TELEGRAM_COUNT})
        )
        assert e.entity_type == EntityType.METADATA

    def test_motion_gives_binary(self):
        e = Entity(id="motion", observables=frozenset({Observable.MOTION}))
        assert e.entity_type == EntityType.BINARY

    def test_contact_state_gives_binary(self):
        e = Entity(id="contact", observables=frozenset({Observable.CONTACT_STATE}))
        assert e.entity_type == EntityType.BINARY

    def test_switch_state_without_actions_gives_binary(self):
        # Read-only actuator status — no SET_SWITCH_OUTPUT action.
        e = Entity(id="status", observables=frozenset({Observable.SWITCH_STATE}))
        assert e.entity_type == EntityType.BINARY

    def test_temperature_gives_sensor(self):
        e = Entity(id="temperature", observables=frozenset({Observable.TEMPERATURE}))
        assert e.entity_type == EntityType.SENSOR

    def test_illumination_gives_sensor(self):
        e = Entity(id="illumination", observables=frozenset({Observable.ILLUMINATION}))
        assert e.entity_type == EntityType.SENSOR

    def test_window_state_gives_sensor(self):
        # WINDOW_STATE is ENUM kind with no actions → falls through to SENSOR.
        e = Entity(id="window_state", observables=frozenset({Observable.WINDOW_STATE}))
        assert e.entity_type == EntityType.SENSOR

    def test_valve_position_gives_sensor(self):
        e = Entity(
            id="valve_position", observables=frozenset({Observable.VALVE_POSITION})
        )
        assert e.entity_type == EntityType.SENSOR


# ---------------------------------------------------------------------------
# Priority: instructable beats observable kind
# ---------------------------------------------------------------------------


class TestEntityTypePriority:
    """Instructable-based classification takes precedence over observable kind."""

    def test_switch_state_with_set_switch_output_gives_switch_not_binary(self):
        e = Entity(
            id="relay",
            observables=frozenset({Observable.SWITCH_STATE}),
            actions=frozenset({Instructable.SET_SWITCH_OUTPUT}),
        )
        assert e.entity_type == EntityType.SWITCH
        assert e.entity_type != EntityType.BINARY
