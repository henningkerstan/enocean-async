"""Stable semantic observable constants shared across capabilities and EEP definitions."""

from enum import Enum

from .value_kind import ValueKind

_S = ValueKind.SCALAR
_B = ValueKind.BINARY
_E = ValueKind.ENUM


class Observable(str, Enum):
    """Stable names for observable quantities exposed by devices.

    Each member has four intrinsic properties:
    - ``name`` - its string value (the semantic id, e.g. "temperature") — used as dict key and in comparisons.
    - ``unit`` — the physical unit for that quantity (``None`` for dimensionless
      or categorical values). Units are domain-conventional (IoT / building automation domain),
      not necessarily SI base units (e.g. °C rather than K, Wh rather than J).
    - ``kind`` — the nature of the value: ``SCALAR`` (continuous numeric), ``BINARY``
      (two-state), or ``ENUM`` (multi-value named set).
    - ``possible_values`` — for ``ENUM``-kinded observables, the exhaustive list of
      string values the observable can take; ``None`` for SCALAR/BINARY observables.
    """

    def __new__(
        cls,
        name: str,
        unit: str | None = None,
        kind: ValueKind = ValueKind.SCALAR,
        possible_values: list[str] | None = None,
    ):
        obj = str.__new__(cls, name)
        obj._value_ = name
        obj.unit = unit
        obj.kind = kind
        obj.possible_values = possible_values
        return obj

    # Sensor values
    TEMPERATURE = ("temperature", "°C", _S)
    HUMIDITY = ("humidity", "%", _S)
    ILLUMINATION = ("illumination", "lx", _S)
    MOTION = ("motion", None, _B)
    VOLTAGE = ("voltage", "V", _S)

    # Cover / blind control
    POSITION = ("position", "%", _S)
    ANGLE = ("angle", "%", _S)
    COVER_STATE = (
        "cover_state",
        None,
        _E,
        ["open", "opening", "closed", "closing", "stopped"],
    )

    # Window handle
    WINDOW_STATE = ("window_state", None, _E, ["open", "tilted", "closed"])

    # Switch / dimmer actuator
    SWITCH_STATE = ("switch_state", None, _B)
    OUTPUT_VALUE = ("output_value", "%", _S)
    ERROR_LEVEL = ("error_level", None, _B)
    PILOT_WIRE_MODE = (
        "pilot_wire_mode",
        None,
        _E,
        ["Off", "Comfort", "Eco", "Anti-freeze", "Comfort-1", "Comfort-2"],
    )

    # Button / occupancy / contact
    BUTTON_EVENT = (
        "button_event",
        None,
        _E,
        ["pressed", "clicked", "held", "released"],
    )
    CONTACT_STATE = ("contact_state", None, _B)
    DAY_NIGHT = ("day_night", None, _B)
    OCCUPANCY_BUTTON = ("occupancy_button", None, _B)

    # Room operating panel controls
    FAN_SPEED = ("fan_speed", None, _S)
    SET_POINT = ("set_point", None, _S)
    TEMPERATURE_SETPOINT = ("temperature_setpoint", "°C", _S)

    # HVAC actuator
    VALVE_POSITION = ("valve_position", "%", _S)

    # Metering
    ENERGY = ("energy", "Wh", _S)
    POWER = ("power", "W", _S)
    GAS_VOLUME = ("gas_volume", "m³", _S)
    GAS_FLOW = ("gas_flow", "l/s", _S)
    WATER_VOLUME = ("water_volume", "m³", _S)
    WATER_FLOW = ("water_flow", "l/s", _S)
    COUNTER = ("counter", None, _S)
    COUNTER_RATE = ("counter_rate", None, _S)

    # Metadata
    RSSI = ("rssi", "dBm", _S)
    LAST_SEEN = ("last_seen", None, _S)
    TELEGRAM_COUNT = ("telegram_count", None, _S)

    # Gateway
    TELEGRAMS_RECEIVED = ("telegrams_received", None, _S)
    TELEGRAMS_SENT = ("telegrams_sent", None, _S)
    CONNECTION_STATUS = (
        "connection_status",
        None,
        _E,
        ["connected", "disconnected", "reconnecting"],
    )
