# Changelog

## [0.7.0] — 2026-03-13

### Breaking changes
- `start_learning()` parameter renamed: `timeout_seconds` → `timeout`; default changed from 60 to 30
- `start_learning()` now raises `RuntimeError` immediately if the gateway's base ID is not yet available (previously the error surfaced later at first teach-in)
- `Gateway.add_device()` now raises `ValueError` if the device address is already registered (previously silently overwrote)

### New features
- Full UTE teach-in: EEP validation, auto-registration, bidirectional response, sender pool allocation
- Full UTE teach-out: `TEACH_IN_DELETION` and toggle `TEACH_IN_OR_DELETION_OF_TEACH_IN` handling; requires `allow_teach_out=True` in `start_learning()`
- 4BS teach-in: learning mode guard + auto-registration (with profile); profileless telegrams are logged and ignored
- 4BS teach-in bidirectional response: gateway always echoes the EEP back with `SENDER_ID_STORED` / `EEP_SUPPORTED` result bits; `learn_status=RESPONSE` telegrams are discarded to avoid processing loopback responses
- 4BS re-teach-in: same-EEP re-teach-in is acknowledged and ignored; EEP-change re-teach-in updates the registered EEP and responds `ACCEPTED`
- 1BS teach-in: learning mode guard; `NewDeviceCallback` fires; no auto-registration (no EEP in telegram)
- `DeviceTaughtInCallback = Callable[[EURID, EEP], None]` — fires after successful teach-in and auto-registration
- `Gateway.add_device_taught_in_callback()` to register teach-in callbacks
- `EEPSpecification.uses_addressed_sending: bool` flag to distinguish destination-addressed (VLD) from sender-addressed (4BS actuator) devices; `A5-38-08` and `A5-20-01` set to `False`
- `start_learning()` log message now shows the effective sender address(es) — addressed devices (BaseID+0) and the next available sender-addressed slot

### Internal / maintenance
- Sender address pool: lowest free BaseID+1…+127 slot allocated at teach-in time for sender-addressed devices; derived on-demand from device registry
- UTE response encoding (`to_erp1()`) completed; `from_erp1()` length check corrected
- 4BS teach-in classes (`FourBSTeachInTelegram`, `FourBSLearnType`, `FourBSLearnStatus`, `FourBSTeachInResult`, `FourBSEEPResult`) moved to `protocol/erp1/fourbs.py`
- Docs moved to `docs/` folder; all README cross-links updated to absolute GitHub URLs


## [0.6.0] — 2026-03-08

### Breaking changes
- `Observation` fields renamed: `device_id` → `device`, `entity_id` → `entity`
- `Observation.time_elapsed` removed
- `EEPMessage.interpreted_values` renamed to `decoded`; `ValueWithUnit` renamed to `ValueWithContext` (with new optional `name` field)
- `Device.address` restricted to `EURID` only (was `EURID | BaseAddress`)
- `Gateway`'s device registry now only allows to register `EURID`s; also the new device callback only is emitted on `EURID`s
- `Device.telegrams_received` removed (was dead code)
- `NewDeviceCallback` now only fires for EURID senders; BaseAddress senders are silently tracked

### Internal / maintenance
- Single `__devices: dict[EURID, Device]` registry replaces the previous two-dict approach (`__known_device_eeps` + `__devices`)
- Docstrings added to `Observation` and `ObservationSource`


## [0.5.3] — 2026-03-07

### Bug fixes
- Fixed A5-02 temperature family readings


## [0.5.2] — 2026-03-07

### Internal / maintenance
- Simplified PushButton state machine


## [0.5.1] — 2026-03-07

### New features
- Added `value_kind` and `entity_kind` to observations


## [0.5.0] — 2026-03-06

### Breaking changes
- Major semantic refactoring: `Capability` renamed to `Observer`; `EntityStateChange` renamed to `Observation`
- `ObservableUID` → `Observable`; `ActionUID` → `Action`; `Action` → `Command`
- ERP1/ESP3 modules moved into `protocol` subpackage
- Receive and send sides made structurally comparable via `Instructable`/`Instruction`
- Device and version model flattened

### New features
- Push-button events renamed for clarity

### Internal / maintenance
- Restructured into submodules; updated documentation


## [0.4.2] — 2026-03-07 (retroactive patch)

### Bug fixes
- Fixed inverted temperature range in EEP A5-02 (range minimum was treated as maximum)


## [0.4.1] — 2026-03-01

### New features
- Added EEP A5-20-01 (HVAC valve actuator) and the full A5-10 family (room operating panels)
- Added support for inverted ranges in scalar decoding (where `min_range > max_range` in the EEP spec)
- Improved binary enum handling in the A5-10 family


## [0.4.0] — 2026-03-01

### Breaking changes
- Revised public API exports — some symbols moved or renamed (see `enocean_async/__init__.py`)


## [0.3.0] — 2026-03-01

### Breaking changes
- Major refactoring introducing new wording and semantics throughout the library
- Typed `Action` system introduced; send pipeline restructured
- Command byte added to telegrams

### New features
- Full UTE teach-in support (automatic bidirectional response)
- EEP D2-01 family: multi-channel support with channel distinction
- Auto-reconnect on connection loss
- Typed Actions for the send pipeline


## [0.2.0] — 2026-02-24

### Breaking changes
- Architecture change: device type removed; capabilities moved to EEP layer

### New features
- EEP A5-02 temperature sensor family
- EEP A5-06 / A5-07-03 illumination and voltage / motion sensors
- EEP A5-08 light, temperature and occupancy sensors
- EEP A5-38-08 dimmer gateway (dimming command)
- EEP D2-05-00 cover (position/angle receive and query)
- EEP D2-20-02 fan speed controller
- EEP F6-10-00 window handle
- EEP 4BS teach-in telegram parsing
- Metadata capability: RSSI, last-seen timestamp, telegram count
- Cover state inference (`OPEN`/`CLOSED`/`PARTIALLY_OPEN`)
- Push button release timeout
- Destination address field in `EEPMessage`
- Passive EEP parsing for unknown senders when destination is known


## [0.1.1] — 2026-02-18

### Bug fixes
- Fixed `ERP1Telegram.__eq__`
- Improved gateway connection error message


## [0.1.0] — 2026-02-17

### New features
- Sender filter on ERP1/EEP callbacks
- Callback for parsing failures
- Device registration / deregistration on the gateway
- Learning mode with configurable timeout
- UTE teach-in: manufacturer information parsing
- `Manufacturers` enum
- Decoder for EEP F6-02-XX rocker switches
- Partial implementation of EEP D2-20-00
- `add_response_callback` function
- Improved logging throughout

### Internal / maintenance
- Refactored into separate protocol and gateway modules
- New EEP key-value dict approach (replaces dedicated subclasses)


## [0.0.2] — 2026-02-10

### Internal / maintenance
- Renamed example scripts


## [0.0.1] — 2026-02-08

Initial release.

### New features
- ESP3 frame parsing and async serial communication
- ERP1 telegram parsing (RORG, sender EURID, RSSI, security level)
- Base ID read and write (with write-cycle counter)
- Additional gateway callbacks
- Basic packet parsing with CRC validation
