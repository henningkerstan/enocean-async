#!/usr/bin/env python3
"""
This script generates a markdown file listing all supported EnOcean Equipment Profiles (EEPs) based on the EEP database in the `enocean_async` library.
The generated file is named `PROFILES.md` and contains a table with the EEP ID and its corresponding name.
"""
from enocean_async.capabilities.entity_uids import EntityUID
from enocean_async.capabilities.metadata import MetaDataCapability
from enocean_async.capabilities.position_angle import PositionAngleCapability
from enocean_async.capabilities.push_button import (
    F6_02_01_02PushButtonCapability,
    PushButtonCapability,
)
from enocean_async.capabilities.scalar_sensor import ScalarSensorCapability
from enocean_async.eep import EEP_DATABASE

# Mapping of capability classes to their emitted StateChange entity_uids and possible values
_BUTTON_EVENTS = ["pushed", "click", "double-click", "hold", "released"]

CAPABILITY_STATE_CHANGES = {
    F6_02_01_02PushButtonCapability: {
        "entities": {
            "a0": _BUTTON_EVENTS,
            "a1": _BUTTON_EVENTS,
            "b0": _BUTTON_EVENTS,
            "b1": _BUTTON_EVENTS,
            "ab0": _BUTTON_EVENTS,
            "ab1": _BUTTON_EVENTS,
            "a0b1": _BUTTON_EVENTS,
            "a1b0": _BUTTON_EVENTS,
        },
    },
    PushButtonCapability: {
        "entities": {
            "{button_id}": _BUTTON_EVENTS,
        },
    },
    PositionAngleCapability: {
        "entities": {
            EntityUID.POSITION: ["position (0-127)"],
            EntityUID.ANGLE: ["angle (0-127)"],
            EntityUID.COVER_STATE: ["open", "opening", "closed", "closing", "stopped"],
        },
    },
    MetaDataCapability: {
        "entities": {
            EntityUID.RSSI: ["signal strength (dBm)"],
            EntityUID.LAST_SEEN: ["timestamp"],
            EntityUID.TELEGRAM_COUNT: ["count"],
        },
    },
}

_SCALAR_ENTITY_DESCRIPTIONS = {
    EntityUID.TEMPERATURE: "temperature (°C)",
    EntityUID.HUMIDITY: "humidity (%)",
    EntityUID.ILLUMINATION: "illumination (lx)",
    EntityUID.MOTION: "motion detected / no motion / uncertain",
    EntityUID.VOLTAGE: "voltage (V)",
    EntityUID.WINDOW_STATE: "window state (open / tilted / closed)",
    EntityUID.OCCUPANCY_BUTTON: "occupancy button (pressed / released)",
}


def get_state_changes_for_eep(eep):
    """Get formatted list of StateChange entity_uids with their values for a given EEP."""
    if not eep.capability_factories:
        return None

    entity_strings = []
    for factory in eep.capability_factories:
        try:
            dummy = factory(None, None)
            capability_class = type(dummy)

            if isinstance(dummy, ScalarSensorCapability):
                uid = dummy.entity_uid
                desc = _SCALAR_ENTITY_DESCRIPTIONS.get(uid, uid)
                entity_strings.append(f"`{uid}`: {desc}")
            elif capability_class in CAPABILITY_STATE_CHANGES:
                entities = CAPABILITY_STATE_CHANGES[capability_class]["entities"]
                for entity_uid, values in entities.items():
                    values_str = ", ".join(f"`{v}`" for v in values)
                    entity_strings.append(f"`{entity_uid}`: {values_str}")
        except Exception:
            pass

    return entity_strings if entity_strings else None


with open("PROFILES.md", "w", encoding="utf-8") as file:
    file.write("# List of supported EnOcean Equipment Profiles (EEPs)\n")
    file.write("<!-- This file is auto-generated via a pre-commit hook, do not edit manually. -->\n\n")
    file.write("All EEPs listed below have three metadata sensors `rssi` (the signal strength in dBm), `last_seen` (the timestamp of the last received telegram), and `telegram_count` (the number of telegrams received since startup) in addition to the listed State Change Events.\n\n")
    file.write("| RORG | FUNC | TYPE | Name | Telegrams | StateChange Events |\n")
    file.write("|---|---|---|---|---|---|\n")

    sorted_eeps = sorted(EEP_DATABASE.values(), key=lambda item: item.id.to_string())

    for entry in sorted_eeps:
        rorg = f"{entry.id.rorg:02X}"
        func = f"{entry.id.func:02X}"
        type_ = f"{entry.id.type:02X}"

        telegrams_supported = "`0x0` (single message EEP)"
        if entry.cmd_offset is not None and entry.cmd_size > 0:
            telegrams_supported = ""
            for key, telegram in sorted(entry.telegrams.items(), key=lambda item: item[0]):
                telegrams_supported += f"`{key:#x}`: {telegram.name}<br>"

        entity_strings = get_state_changes_for_eep(entry)
        entity_uids_str = "<br>".join(entity_strings) if entity_strings else "—"

        file.write(
            f"| {rorg} | {func} | {type_} | {entry.name} | {telegrams_supported} | {entity_uids_str} |\n"
        )
