"""Stable semantic entity UID constants shared across capabilities and EEP definitions."""


class EntityUID:
    """Semantic entity UIDs used in StateChange emissions and EEP field annotations.

    These are the canonical names for observable quantities, independent of the
    EEP spec field IDs (which may vary across profiles).
    """

    # Sensor values
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    ILLUMINATION = "illumination"
    MOTION = "motion"
    VOLTAGE = "voltage"

    # Cover / blind control
    POSITION = "position"
    ANGLE = "angle"
    COVER_STATE = "cover_state"

    # Window handle
    WINDOW_STATE = "window_state"

    # Button / occupancy
    OCCUPANCY_BUTTON = "occupancy_button"

    # Metadata
    RSSI = "rssi"
    LAST_SEEN = "last_seen"
    TELEGRAM_COUNT = "telegram_count"
