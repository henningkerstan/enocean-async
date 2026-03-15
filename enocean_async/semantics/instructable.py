"""Stable semantic action constants for commands sent to devices."""

from enum import StrEnum


class Instructable(StrEnum):
    """Stable names for actions that can be commanded to devices.

    These are the canonical identifiers for things you can command a device to do —
    independent of the EEP spec field IDs. Analogous to Observable but for the
    send direction.
    """

    # Cover control (D2-05-00, A5-38-08 CMD 0x07)
    COVER_SET_POSITION = "cover_set_position"
    COVER_STOP = "cover_stop"
    COVER_QUERY_POSITION = "cover_query_position"
    COVER_OPEN = "cover_open"
    COVER_CLOSE = "cover_close"

    # Central command — lighting (A5-38-08 CMD 0x01, 0x02)
    SWITCH = "switch"
    DIM = "dim"

    # Fan control (D2-20-02)
    SET_FAN_SPEED = "set_fan_speed"

    # Electronic switches and dimmers (D2-01)
    SET_SWITCH_OUTPUT = "set_switch_output"
    QUERY_ACTUATOR_STATUS = "query_actuator_status"
    QUERY_ACTUATOR_MEASUREMENT = "query_actuator_measurement"
