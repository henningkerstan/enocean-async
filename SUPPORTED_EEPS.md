# List of supported EnOcean Equipment Profiles (EEPs)
<!-- This file is auto-generated via a pre-commit hook, do not edit manually. -->

All EEPs listed below have three metadata sensors `rssi` (the signal strength in dBm), `last_seen` (the timestamp of the last received telegram), and `telegram_count` (the number of telegrams received since startup) in addition to the listed State Change Events.

| RORG | FUNC | TYPE | Name | Telegrams | StateChange Events |
|---|---|---|---|---|---|
| A5 | 02 | 01 | Temperature sensor, range -40.0°C to 0.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 02 | Temperature sensor, range -30.0°C to 10.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 03 | Temperature sensor, range -20.0°C to 20.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 04 | Temperature sensor, range -10.0°C to 30.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 05 | Temperature sensor, range 0.0°C to 40.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 06 | Temperature sensor, range 10.0°C to 50.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 07 | Temperature sensor, range 20.0°C to 60.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 08 | Temperature sensor, range 30.0°C to 70.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 09 | Temperature sensor, range 40.0°C to 80.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 0A | Temperature sensor, range 50.0°C to 90.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 0B | Temperature sensor, range 60.0°C to 100.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 10 | Temperature sensor, range -60.0°C to 20.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 11 | Temperature sensor, range -50.0°C to 30.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 12 | Temperature sensor, range -40.0°C to 40.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 13 | Temperature sensor, range -30.0°C to 50.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 14 | Temperature sensor, range -20.0°C to 60.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 15 | Temperature sensor, range -10.0°C to 70.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 16 | Temperature sensor, range 0.0°C to 80.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 17 | Temperature sensor, range 10.0°C to 90.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 18 | Temperature sensor, range 20.0°C to 100.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 19 | Temperature sensor, range 30.0°C to 110.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 1A | Temperature sensor, range 40.0°C to 120.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 1B | Temperature sensor, range 50.0°C to 130.0°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 20 | 10 bit temperature sensor, range -10.0°C to 41.2°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 02 | 30 | 10 bit temperature sensor, range -40.0°C to 62.3°C | `0x0` (single message EEP) | `temperature`: temperature (°C) |
| A5 | 04 | 01 | Temperature and humidity sensor, range 0.0°C to 40.0°C and 0% to 100% | `0x0` (single message EEP) | `humidity`: humidity (%)<br>`temperature`: temperature (°C) |
| A5 | 04 | 02 | Temperature and humidity sensor, range -20.0°C to 60.0°C and 0% to 100% | `0x0` (single message EEP) | `humidity`: humidity (%)<br>`temperature`: temperature (°C) |
| A5 | 04 | 03 | Temperature and humidity sensor, range -20°C to 60°C 10bit-measurement and 0% to 100% | `0x0` (single message EEP) | `humidity`: humidity (%)<br>`temperature`: temperature (°C) |
| A5 | 06 | 01 | Light sensor, range 300.0lx to 60000.0lx | `0x0` (single message EEP) | `illumination`: illumination (lx) |
| A5 | 06 | 01 | Light sensor (Eltako variant), dual-range 0–100lx / 300–30000lx | `0x0` (single message EEP) | `illumination`: illumination (lx) |
| A5 | 06 | 02 | Light sensor, range 0.0lx to 1020.0lx | `0x0` (single message EEP) | `illumination`: illumination (lx) |
| A5 | 06 | 03 | Light sensor, 10-bit measurement, range 0lx to 1000lx | `0x0` (single message EEP) | `illumination`: illumination (lx) |
| A5 | 06 | 04 | Curtain wall brightness sensor | `0x0` (single message EEP) | `illumination`: illumination (lx)<br>`temperature`: temperature (°C) |
| A5 | 06 | 05 | Light sensor, range 0.0lx to 10200.0lx | `0x0` (single message EEP) | `illumination`: illumination (lx) |
| A5 | 07 | 03 | Occupancy with supply voltage monitor and 10-bit illumination measurement | `0x0` (single message EEP) | `voltage`: voltage (V)<br>`illumination`: illumination (lx)<br>`motion`: motion detected / no motion / uncertain |
| A5 | 08 | 01 | Light, temperature and occupancy sensor, range 0lx to 510lx, 0.0°C to 51.0°C and occupancy button | `0x0` (single message EEP) | `voltage`: voltage (V)<br>`illumination`: illumination (lx)<br>`temperature`: temperature (°C)<br>`motion`: motion detected / no motion / uncertain<br>`occupancy_button`: occupancy button (pressed / released) |
| A5 | 08 | 01 | Light and occupancy sensor, range 0lx to 510lx, Eltako variant (FABH65S, FBH65, FBH65TF, FBH65SB, FBH55SB, FBHF65SB, F4USM61B) | `0x0` (single message EEP) | `voltage`: voltage (V)<br>`illumination`: illumination (lx)<br>`motion`: motion detected / no motion / uncertain |
| A5 | 08 | 02 | Light, temperature and occupancy sensor, range 0lx to 1020lx, 0.0°C to 51.0°C and occupancy button | `0x0` (single message EEP) | `voltage`: voltage (V)<br>`illumination`: illumination (lx)<br>`temperature`: temperature (°C)<br>`motion`: motion detected / no motion / uncertain<br>`occupancy_button`: occupancy button (pressed / released) |
| A5 | 08 | 03 | Light, temperature and occupancy sensor, range 0lx to 1530lx, -30.0°C to 50.0°C and occupancy button | `0x0` (single message EEP) | `voltage`: voltage (V)<br>`illumination`: illumination (lx)<br>`temperature`: temperature (°C)<br>`motion`: motion detected / no motion / uncertain<br>`occupancy_button`: occupancy button (pressed / released) |
| A5 | 38 | 08 | Central command - gateway | `0x2`: Dimming<br> | — |
| D2 | 05 | 00 | Blinds control for position and angle, type 0x00 | `0x1`: Go to position and angle<br>`0x2`: Stop<br>`0x3`: Query position and angle<br>`0x4`: Reply position and angle<br> | `position`: `position (0-127)`<br>`angle`: `angle (0-127)`<br>`cover_state`: `open`, `opening`, `closed`, `closing`, `stopped` |
| D2 | 20 | 02 | Fan control, type 0x02 | `0x0`: Fan control message<br>`0x1`: Fan status message<br> | — |
| F6 | 02 | 01 | Light and blind control - application style 1 | `0x0` (single message EEP) | `a0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`b0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`b1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`ab0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`ab1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a0b1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a1b0`: `pushed`, `click`, `double-click`, `hold`, `released` |
| F6 | 02 | 02 | Light and blind control - application style 2 | `0x0` (single message EEP) | `a0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`b0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`b1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`ab0`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`ab1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a0b1`: `pushed`, `click`, `double-click`, `hold`, `released`<br>`a1b0`: `pushed`, `click`, `double-click`, `hold`, `released` |
| F6 | 10 | 00 | Window handle | `0x0` (single message EEP) | `window_state`: window state (open / tilted / closed) |
| F6 | 10 | 00 | Window handle (Eltako variant) | `0x0` (single message EEP) | `window_state`: window state (open / tilted / closed) |
