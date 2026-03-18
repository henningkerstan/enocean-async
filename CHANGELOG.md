# Changelog

## [0.7.0] — 2026-03-14

### Breaking changes
- `EEP` constructor redesigned: accepts `str | list[int]` instead of positional ints; `from_string()` classmethod removed; `__repr__` now returns `"A5-02-05"` (not `"EEP(A5-02-05)"`)
  - String form: `EEP("A5-02-05")`, `EEP("A5-08-01", Manufacturer.ELTAKO)`
  - List form for protocol-level use: `EEP([0xA5, 0x02, 0x05])`
- `start_learning()` parameter renamed: `timeout_seconds` → `timeout`; default changed from 60 to 30
- `start_learning()` now raises `RuntimeError` immediately if the gateway's base ID is not yet available (previously the error surfaced later at first teach-in)
- `Gateway.add_device()` signature changed: `eep: EEP` replaced by `device_type: DeviceType`; use `DeviceType.for_eep(EEP("F6-02-01"))` to obtain a generic DeviceType from an EEP string
- `Gateway.add_device()` now raises `ValueError` if the device address is already registered (previously silently overwrote)
- `Device.eep` is now a read-only property backed by `Device.device_type`; `Device.device_type: DeviceType` is the new primary field
- `Address` API simplified — removed `to_number()` (use `int(addr)`), `to_string()` (use `str(addr)`), `to_bytelist()` (use `.bytelist`), `to_json()`, `from_number()`, `from_string()` (pass value directly to constructor), `broadcast()`, and `validate_string()`
- `Gateway.entities()` renamed to `Gateway.device_specs` (now a `@property`)
- `DeviceDescriptor` renamed to `DeviceSpec`; module `semantics/device_descriptor.py` → `semantics/device_spec.py`; `Gateway.device_descriptor(address)` → `Gateway.device_spec(address)`; `Gateway.device_descriptors` → `Gateway.device_specs`
- `Observable.PUSH_BUTTON` renamed to `Observable.BUTTON_EVENT` (string value `"button_event"`)
- `EntityType.PUSH_BUTTON` renamed to `EntityType.BUTTON` (string value `"button"`)
- `PushButtonObserver` renamed to `ButtonObserver`; `F6_02_01_02PushButtonObserver` → `F6_02_01_02_ButtonObserver`; `f6_push_button_factory()` → `f6_button_factory()`; module `semantics/observers/push_button.py` → `semantics/observers/button.py`
- `Manufacturer` enum redesigned: previously a `StrEnum` (member value = display name); now a plain `Enum` with `(id: int | None, display_name: str)` tuple values. Access the 11-bit Alliance code via `.id` (or `None` for non-Alliance members); display name via `.display_name` or `str(m)`; reverse lookup via `Manufacturer.from_id(id)`. Enum member names stripped of legal-entity suffixes (`ENOCEAN_GMBH` → `ENOCEAN`, `PERMUNDO_GMBH` → `PERMUNDO`, `HOPPE_HOLDING_AG` → `HOPPE`, etc.) and generic descriptors shortened (`EUROTRONIC_TECHNOLOGY_GMBH` → `EUROTRONIC`, `AWAG_ELEKTROTECHNIK_AG` → `AWAG`, `DEUTA_CONTROLS_GMBH` → `DEUTA`, etc.); also fixes two typos (`HUBBEL_LIGHTNING` → `HUBBELL`, `AUTANI_LCC` → `AUTANI`). `ManufacturerID` (separate IntEnum) is removed — its functionality is merged into `Manufacturer.id`.

### New features
- **`DeviceType` catalog** (`eep/device_type.py`): associates a manufacturer and model name with an EEP. The catalog (`DEVICE_TYPES`) contains generic entries (auto-derived from `EEP_SPECIFICATIONS`, one per supported EEP) and manufacturer-specific entries (known physical products). Key API:
  - `DeviceType(manufacturer, model, eep, description)` — frozen dataclass
  - `DeviceType.for_eep(eep) -> DeviceType` — class-method factory; raises `ValueError` for unsupported EEPs
  - `DeviceType.identifier` — stable `{NAMESPACE}/{CODE}` string (e.g. `"EEP/A5-02-01"`, `"ELTAKO/FAH65S"`, `"ELTAKO/A5-06-01"` for an Eltako-specific EEP variant)
  - `DEVICE_TYPES: list[DeviceType]` — full catalog, exported from top-level package
- Full UTE teach-in: EEP validation, auto-registration, bidirectional response, sender pool allocation
- Full UTE teach-out: `TEACH_IN_DELETION` and toggle `TEACH_IN_OR_DELETION_OF_TEACH_IN` handling; requires `allow_teach_out=True` in `start_learning()`
- 4BS teach-in: learning mode guard + auto-registration (with profile); profileless telegrams are logged and ignored
- 4BS teach-in bidirectional response: gateway always echoes the EEP back with `SENDER_ID_STORED` / `EEP_SUPPORTED` result bits; `learn_status=RESPONSE` telegrams are discarded to avoid processing loopback responses
- 4BS re-teach-in: same-EEP re-teach-in is acknowledged and ignored; EEP-change re-teach-in updates the registered EEP and responds `ACCEPTED`
- 1BS teach-in: learning mode guard; `NewDeviceCallback` fires; no auto-registration (no EEP in telegram)
- `DeviceTaughtInCallback = Callable[[TaughtInDevice], None]` — fires after successful teach-in and auto-registration
- `Gateway.add_device_taught_in_callback()` to register teach-in callbacks
- `TaughtInDevice` dataclass (fields: `address: EURID`, `eep: EEP`) exported from `enocean_async`
- `EEPSpecification.uses_addressed_sending: bool` flag to distinguish destination-addressed (VLD) from sender-addressed (4BS actuator) devices; `A5-38-08` and `A5-20-01` set to `False`
- `start_learning()` log message now shows the effective sender address(es) — addressed devices (BaseID+0) and the next available sender-addressed slot
- `Address` constructor now accepts `bytes`, `bytearray`, or `list[int]` (4-element big-endian) in addition to `int` and `str`
- `Address.bytelist` property (replaces `to_bytelist()` method)
- `Entity` exported from the top-level `enocean_async` package

### Bug fixes
- `BaseAddress` upper bound corrected from `FF:FF:FF:80` to `FF:FF:FF:FE` (the broadcast address `FF:FF:FF:FF` is excluded; valid base address sender slots extend to `FF:FF:FF:FE`)
- D2-01 channel entity_ids changed from observable-name strings (`"switch_state"`, `"output_value"`, …) to `"ch1_switch_state"`, `"ch2_switch_state"`, … (channel-prefixed, 1-indexed, one entity per observable)
- `gateway.remove_device()` now calls `observer.stop()` on all observers before deregistering; `CoverObserver.stop()` cancels the watchdog timer handle and `ButtonObserver.stop()` cancels hold/release timers, preventing asyncio task leaks

### Internal / maintenance
- Sender address pool: lowest free BaseID+1…+127 slot allocated at teach-in time for sender-addressed devices; derived on-demand from device registry
- UTE response encoding (`to_erp1()`) completed; `from_erp1()` length check corrected
- 4BS teach-in classes (`FourBSTeachInTelegram`, `FourBSLearnType`, `FourBSLearnStatus`, `FourBSTeachInResult`, `FourBSEEPResult`) moved to `protocol/erp1/fourbs.py`
- Docs moved to `docs/` folder; all README cross-links updated to absolute GitHub URLs
- `Entity` and `EntityType` moved to `semantics/entity.py` (merged from separate `entity_type.py`)
- `ObserverFactory` moved to `semantics/observer_factory.py`; `SemanticResolver` and `InstructionEncoder` type aliases moved to `semantics/types.py`; `DeviceSpec` moved to `semantics/device_spec.py`; all re-exported from `eep/profile.py` for backward compatibility
- D2-01 `EEPSpecification` now carries static `entities` derived from per-variant `channels`, `dimming`, `metering`, and `pilot_wire` flags; one `Entity` per observable per channel (`"ch1_switch_state"`, `"ch1_error_level"`, …); `ScalarObserver` gains `entity_id_prefix` / `entity_id_offset` / `entity_id_suffix` parameters to support the `"ch{n}_{observable}"` naming scheme
- `Observer.stop()` no-op added to base class; `gateway.remove_device()` calls it on all registered observers; `ButtonObserver.stop()` cancels pending hold/release timer handles
- `CoverObserver` watchdog refactored from `asyncio.Task` + `await asyncio.sleep()` to `loop.call_later()` / `asyncio.TimerHandle`; eliminates the `try/except CancelledError` guard


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
