# List of supported EnOcean Equipment Profiles (EEPs)
<!-- This file is auto-generated via a pre-commit hook, do not edit manually. -->

| EEP | Name | Telegrams | StateChange Entity UIDs |
|---|---|---|---|
| A5-02-01 | Temperature sensor, range -40.0°C to 0.0°C | `0x0` (single message EEP) | — |
| A5-02-02 | Temperature sensor, range -30.0°C to 10.0°C | `0x0` (single message EEP) | — |
| A5-02-03 | Temperature sensor, range -20.0°C to 20.0°C | `0x0` (single message EEP) | — |
| A5-02-04 | Temperature sensor, range -10.0°C to 30.0°C | `0x0` (single message EEP) | — |
| A5-02-05 | Temperature sensor, range 0.0°C to 40.0°C | `0x0` (single message EEP) | — |
| A5-02-06 | Temperature sensor, range 10.0°C to 50.0°C | `0x0` (single message EEP) | — |
| A5-02-07 | Temperature sensor, range 20.0°C to 60.0°C | `0x0` (single message EEP) | — |
| A5-02-08 | Temperature sensor, range 30.0°C to 70.0°C | `0x0` (single message EEP) | — |
| A5-02-09 | Temperature sensor, range 40.0°C to 80.0°C | `0x0` (single message EEP) | — |
| A5-02-0A | Temperature sensor, range 50.0°C to 90.0°C | `0x0` (single message EEP) | — |
| A5-02-0B | Temperature sensor, range 60.0°C to 100.0°C | `0x0` (single message EEP) | — |
| A5-02-10 | Temperature sensor, range -60.0°C to 20.0°C | `0x0` (single message EEP) | — |
| A5-02-11 | Temperature sensor, range -50.0°C to 30.0°C | `0x0` (single message EEP) | — |
| A5-02-12 | Temperature sensor, range -40.0°C to 40.0°C | `0x0` (single message EEP) | — |
| A5-02-13 | Temperature sensor, range -30.0°C to 50.0°C | `0x0` (single message EEP) | — |
| A5-02-14 | Temperature sensor, range -20.0°C to 60.0°C | `0x0` (single message EEP) | — |
| A5-02-15 | Temperature sensor, range -10.0°C to 70.0°C | `0x0` (single message EEP) | — |
| A5-02-16 | Temperature sensor, range 0.0°C to 80.0°C | `0x0` (single message EEP) | — |
| A5-02-17 | Temperature sensor, range 10.0°C to 90.0°C | `0x0` (single message EEP) | — |
| A5-02-18 | Temperature sensor, range 20.0°C to 100.0°C | `0x0` (single message EEP) | — |
| A5-02-19 | Temperature sensor, range 30.0°C to 110.0°C | `0x0` (single message EEP) | — |
| A5-02-1A | Temperature sensor, range 40.0°C to 120.0°C | `0x0` (single message EEP) | — |
| A5-02-1B | Temperature sensor, range 50.0°C to 130.0°C | `0x0` (single message EEP) | — |
| A5-02-20 | 10 bit temperature sensor, range -10.0°C to 41.2°C | `0x0` (single message EEP) | — |
| A5-02-30 | 10 bit temperature sensor, range -40.0°C to 62.3°C | `0x0` (single message EEP) | — |
| A5-07-03 | Occupancy with Supply voltage monitor and 10-bit illumination measurement | `0x0` (single message EEP) | — |
| A5-38-08 | Central Command - Gateway | `0x2`: Dimming<br> | — |
| D2-05-00 | Blinds Control for Position and Angle, Type 0x00 | `0x1`: Go to Position and Angle<br>`0x2`: Stop<br>`0x3`: Query Position and Angle<br>`0x4`: Reply Position and Angle<br> | `POS`: `position (0-127)`<br>`ANG`: `angle (0-127)`<br>`rssi`: `signal strength (dBm)`<br>`last_seen`: `timestamp`<br>`telegram_count`: `count` |
| D2-20-02 | Fan Control, Type 0x02 | `0x0`: Fan Control Message<br>`0x1`: Fan Status Message<br> | — |
| F6-02-01 | Light and Blind Control - Application Style 1 | `0x0` (single message EEP) | `a0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`b0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`b1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`ab0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`ab1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a0b1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a1b0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`rssi`: `signal strength (dBm)`<br>`last_seen`: `timestamp`<br>`telegram_count`: `count` |
| F6-02-02 | Light and Blind Control - Application Style 2 | `0x0` (single message EEP) | `a0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`b0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`b1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`ab0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`ab1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a0b1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a1b0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`rssi`: `signal strength (dBm)`<br>`last_seen`: `timestamp`<br>`telegram_count`: `count` |
