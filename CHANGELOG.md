# Changelog

## [0.12.0] — unreleased

### Breaking changes
- **`Dim.use_relative`** default changed from `True` to `None` (sentinel for "use device config"). Explicit `True`/`False` still works; `None` (the new default) defers to device config `"dimming_mode"` (`"relative"` → EDIMR=1, `"absolute"` → EDIMR=0; falls back to `"relative"`).

### New features
- **A5-38-08 `dimming_mode` config entity** now active: `_DIM_MODE_SELECT` (`EnumOptions(options=("relative", "absolute"), default="relative")`) is consulted by `_encode_dim` when `Dim.use_relative` is `None`.

### Internal / maintenance
- **`py.typed` marker added** (PEP 561): the package now ships inline type information. Type checkers (mypy, pyright, pylance) will pick up type hints automatically without stubs.
- Missing return type annotations added throughout (`gateway.py`, `address.py`, `eep/id.py`, `protocol/esp3/protocol.py`, `semantics/observers/metadata.py`).


## [0.11.0] — 2026-03-24

### Breaking changes
- **`Device.options` → `Device.config`**: the per-device runtime config dict is now `device.config`; update all read / write call sites.
- **`Entity.option_spec` → `Entity.config_spec`**: the EEP-level config spec field is renamed; update any code that accesses this attribute directly.
- **`EntityType.OPTION_ENUM` → `EntityType.CONFIG_ENUM`** (value `"config_enum"`) and **`EntityType.OPTION_NUMBER` → `EntityType.CONFIG_NUMBER`** (value `"config_number"`): update any code matching on these enum members or their string values.
- **`Gateway.set_device_option()` → `Gateway.set_device_config()`**: rename call sites.
- **`Gateway.add_device(options=...)` → `Gateway.add_device(config=...)`**: rename keyword argument.
- **`SemanticResolver` signature extended**: `(raw, scaled) → value` becomes `(raw, scaled, config) → value`; all custom resolver functions must accept a third `config: dict` positional argument (use `_config` if unused).
- **`Dim.ramp_time`** default changed from `0` to `None` (sentinel for "use device config"). Explicit `0` still means "ramp immediately"; `None` (the new default) defers to device config `"ramp_time"` (falls back to `0`). Code that relied on the old `0` default continues to work via config fallback, but typed call sites that previously passed `ramp_time=0` explicitly are unaffected.
- **`Dim.store`** default changed from `False` to `None` (sentinel for "use device config"). Explicit `False`/`True` still works; `None` (the new default) defers to device config `"store"` (falls back to `False`).

### New features
- **`BoolOption(default=False) → EnumOptions`** — convenience factory exported from `enocean_async`; shorthand for `EnumOptions(options=("no", "yes"), default="yes" if default else "no")`.
- **A5-38-08 `store` config entity**: `Entity(id="store", config_spec=BoolOption(), category=CONFIG)` added to the EEP spec; `"store"` is now auto-populated in `Device.config` at `add_device()` time (default `"no"`). The `_encode_dim` encoder maps `"yes"` → `STR=1`, `"no"` → `STR=0`.
- **Inverse brightness scaling in observe path**: A5-38-08 `_resolve_edim` now applies the inverse of the `min_brightness` / `max_brightness` scaling used when sending, so `Observable.OUTPUT_VALUE` is always reported in the caller's 0–100 % range regardless of brightness limits.
- **`EEPHandler.decode(telegram, config=None)`**: the optional `config: dict | None` argument is forwarded to all semantic resolvers; the gateway automatically passes the sender device's `Device.config`.

### Internal / maintenance
- All built-in semantic resolvers updated to the three-argument `(raw, scaled, config)` signature.


## [0.10.0] — 2026-03-23

### Breaking changes
- **F6-02 simultaneous button presses**: combo entity IDs (`ab0`, `ab1`, `a0b1`, `a1b0`) are removed. A two-button press (SA=1) now fires two separate atomic `PRESSED` events — one for each button (`a0`/`a1`/`b0`/`b1`) — with identical timestamps. Update any callback logic that matched on combo entity IDs.

## [0.9.0] — 2026-03-22

### Breaking changes
- `gateway.base_id`, `gateway.eurid`, `gateway.version_info`, `gateway.base_id_remaining_write_cycles` are now plain sync properties returning the cached value (or `None` before `start()`). Remove all `await` from call sites; the values are guaranteed non-`None` after `start()` returns.
- `gateway.is_valid_sender()` is now a sync method (`def`, not `async def`).
- `gateway.sender_slots` is now a plain sync property (no `await` needed); returns `{}` before `start()`.

### New features
- `gateway.fetch_base_id()` and `gateway.fetch_version_info()` — new async methods to explicitly request and cache gateway info from the module; called automatically by `start()`

## [0.8.0] — 2026-03-22

### Breaking changes
- **D2-01**: `QUERY_ACTUATOR_STATUS` and `QUERY_ACTUATOR_MEASUREMENT` instructables moved from the channel switch entity to dedicated `query_status` / `query_measurement` trigger entities. The switch entity now carries only `SET_SWITCH_OUTPUT`.

### New features
- **Gateway device observables**: the gateway itself is now observable. Three entities are available via `gateway.gateway_entities`:
  - `connection_status` — `Observable.CONNECTION_STATUS` (`"connected"` / `"disconnected"` / `"reconnecting"`); source `ObservationSource.GATEWAY`
  - `telegrams_received` — count of ERP1 telegrams received since `start()` (never reset on reconnect)
  - `telegrams_sent` — count of ERP1 telegrams sent since `start()` (never reset on reconnect)
- `add_observation_callback()` immediately replays the current connection status to newly registered subscribers via `loop.call_soon`
- `ObservationSource.GATEWAY = 2` — new source value for gateway-originated observations (connection status changes)
- **A5-38-08 cover receive**: CMD=7 / FUNC=0 / PAF=1 status telegrams are now decoded into `POSITION` (0–100 %) and `ANGLE` (0–100 %) observables; a new `cover` entity exposes `COVER_STATE`, `POSITION`, and `ANGLE`
- **D2-01 trigger entities**: `query_status` entity (all variants) exposes `QUERY_ACTUATOR_STATUS`; `query_measurement` entity (metering variants) exposes `QUERY_ACTUATOR_MEASUREMENT`
- **Entity option defaults**: `EnumOptions.default: str | None` and `NumberRange.default: float | None` added; all built-in configurable entities (dimming mode, brightness limits, ramp time, repositioning mode) carry sensible defaults

### Internal / maintenance
- Teach-in response tasks (UTE + 4BS) stored in `__background_tasks` set and cancelled in `stop()`; eliminates potential "task was destroyed but it is pending" warnings on gateway shutdown

### Bug fixes
- **A5-38-08** missing entity declaration added: `Entity(id="light", observables={OUTPUT_VALUE}, actions={DIM, SWITCH})`; `EntityType.DIMMER` is now discoverable for this EEP

## [0.7.0] — 2026-03-14

### Breaking changes
- `EEP` constructor redesigned: accepts `str | list[int]` instead of positional ints; `from_string()` classmethod removed; `__repr__` now returns `"A5-02-05"` (not `"EEP(A5-02-05)"`)
  - String form: `EEP("A5-02-05")`, `EEP("A5-08-01", Manufacturer.ELTAKO)`
  - List form for protocol-level use: `EEP([0xA5, 0x02, 0x05])`
- `start_learning()` parameter renamed: `timeout_seconds` → `timeout`; default changed from 60 to 30
- `start_learning()` now raises `RuntimeError` immediately if the gateway's base ID is not yet available (previously the error surfaced later at first teach-in)
- `Gateway.add_device()` signature changed: `eep: EEP` replaced by `device_type: DeviceType`; use `device_type_for_eep(EEP("F6-02-01"))` to obtain a generic DeviceType from an EEP string
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
- **`DeviceSpec`** (`semantics/device_spec.py`) — built by `gateway.device_spec()` (no longer a method on `EEPSpecification`); includes `device_type: DeviceType` (manufacturer + model + EEP) and `entities` (from EEP spec + 3 gateway-injected metadata entities).
- **`DEVICE_TYPES: dict[str, DeviceType]`** — O(1) catalog lookup by stable `DeviceType.id` string (e.g. `DEVICE_TYPES["NODON/SIN-2-RS-01"]`); exported from top-level package.
- **`Observable.possible_values: list[str] | None`** — ENUM-kinded observables now carry their possible string values as an intrinsic property. Populated for `BUTTON_EVENT` (`pressed`, `clicked`, `held`, `released`), `COVER_STATE`, `WINDOW_STATE`, and `PILOT_WIRE_MODE`.
- **A5-12-00 through A5-12-03** (automated meter reading): full semantic layer with DT-conditional resolvers — `_cumulative_resolver` / `_current_resolver` factory functions select the correct value and unit based on the `DT` (data-type) flag in each telegram. Observables: `COUNTER` / `COUNTER_RATE` (A5-12-00), `ENERGY` / `POWER` (A5-12-01), `GAS_VOLUME` / `GAS_FLOW` (A5-12-02), `WATER_VOLUME` / `WATER_FLOW` (A5-12-03).
- **New `Observable` metering members**: `GAS_VOLUME` (`"m³"`), `GAS_FLOW` (`"l/s"`), `WATER_VOLUME` (`"m³"`), `WATER_FLOW` (`"l/s"`), `COUNTER` (dimensionless), `COUNTER_RATE` (dimensionless).
- **`DeviceType` catalog** (`eep/device_type.py`): associates a manufacturer and model name with an EEP. The catalog (`DEVICE_TYPES`) contains generic entries (auto-derived from `EEP_SPECIFICATIONS`, one per supported EEP) and manufacturer-specific entries (known physical products). Key API:
  - `DeviceType(manufacturer, model, eep, description)` — frozen dataclass
  - `device_type_for_eep(eep) -> DeviceType` — free function; raises `KeyError` for unsupported EEPs
  - `DeviceType.id` — stable `{NAMESPACE}/{CODE}` string (e.g. `"EEP/A5-02-01"`, `"ELTAKO/FAH65S"`, `"ELTAKO/A5-06-01"` for an Eltako-specific EEP variant)
  - `DEVICE_TYPES: dict[str, DeviceType]` — full catalog keyed by `DeviceType.id`, exported from top-level package
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
- **D2-20-02** missing entity declaration added: `Entity(id="fan", observables={FAN_SPEED}, actions={SET_FAN_SPEED})`; `EntityType.FAN` is now discoverable for this EEP

### Internal / maintenance
- `SUPPORTED_DEVICES.md` replaces `SUPPORTED_EEPS.md`; auto-generated by `scripts/generate_list_of_devices.py` (replaces `generate_list_of_eeps.py`); contains two sections — manufacturer-specific entries (sorted by manufacturer/model) and generic EEP entries (sorted by RORG/func/type) — each with Entities and Instructions columns. A pre-commit hook (`generate-supported-devices`) regenerates it automatically on any change under `enocean_async/eep/`.
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
