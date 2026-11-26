# Changelog

## [0.19.0] — 2026-11-26

### Breaking changes
- **The Eltako FSB profile is named `A5-3F-7F.ELTAKO.FSB`** (was `A5-7F-3F.ELTAKO.FSB`, with FUNC and TYPE swapped): the FSB's learn telegram `FF F8 0D 80` carries FUNC 0x3F and TYPE 0x7F ("universal"), as Eltako's telegram document names it too. The former name is not kept: `EEP("A5-7F-3F.ELTAKO.FSB")` is no longer the FSB profile, and the device type ID `ELTAKO/A5-7F-3F/FSB` and the import name `EEP_A5_7F_3F_ELTAKO_FSB` are gone. An integration that stored one of them must change it to `A5-3F-7F.ELTAKO.FSB`, `ELTAKO/A5-3F-7F/FSB` or `EEP_A5_3F_7F_ELTAKO_FSB`; the device type `ELTAKO/FSB61` is unchanged. Contributed by eltakoal (#19).

### New features
- **Eltako FSB confirmations are read** (`A5-3F-7F.ELTAKO.FSB`, FSB14, FSB61, FSB71): the actuator confirms with RPS telegrams when a movement starts and when it reaches an end position. They are now reported as cover state `opening`, `closing`, `open` and `closed`; before, they were not decoded, and after a full movement no cover state arrived at all. The FSB61NP sends confirmation telegrams only once they are switched on (switched off as delivered; see its manual, "Bestätigungs-Telegramme einschalten"). Contributed by eltakoal (#18).
- **`EEPSpecification.other_rorg_telegrams`**: a profile can declare telegrams its device sends with another RORG than the one of its EEP, with their own data fields; they are decoded and passed to the semantic resolvers. A profile that declares none behaves as before. Contributed by eltakoal (#18).
- **New profiles `A5-14-09`, `A5-09-04` and `A5-07-01`**: a window/door sensor with the states open, closed and tilted and its supply voltage (`window_state`, `supply_voltage`), a CO2 sensor with humidity and temperature (`co2`, `humidity`, `temperature`; new observable `co2` in ppm), and occupancy with a supply voltage monitor (`motion`, `supply_voltage`). Device catalog: Eltako FFG7B (in its delivery state), FCO2TS and FB65B. Contributed by eltakoal (#17).
- **Device catalog: Eltako F2T55E, F4T55E and FMH8** (`F6-02-01`), next to the FT55: the pushbuttons with one and two rockers (also the F2T55EOR and F4T55EOR without frame) and the mini hand-held transmitter with 8 buttons. The FMH8 contains two radio modules, each with its own sender ID (buttons 1–4 and 5–8): an application has to add both IDs as two devices. The catalog description says so, since nothing else would tell a user. No profile change; tested with the devices. Contributed by eltakoal (#16).

### Bug fixes
- **A stopped Eltako FSB cover was reported as `open` or `closed`** (`A5-3F-7F.ELTAKO.FSB`): the FSB sends its 4BS status telegram (travel time and direction) only when a movement is stopped before its run time is up, but the direction was taken as an end position. Such a cover is now reported as `stopped`. A consumer that handled `stopped` only for other covers now also gets it from an FSB. Contributed by eltakoal (#18).
- **A reserved supply voltage value was reported as a voltage above 5 V** (`A5-07-03`, `A5-10-1A`, `A5-10-1B`, `A5-10-1E`): these profiles give the supply voltage a valid range of 0 to 250 (0 to 5.0 V) and reserve 251 to 255 for error codes, which were reported as up to 5.1 V. They now give no voltage, as in the new profiles `A5-07-01` and `A5-14-09`.
- **Eltako FAH65S brightness below 100 lx was reported too low** (`A5-06-01.ELTAKO`): the low range (data byte 3) holds 0 to 100 lx as the raw values 0 to 100, but was scaled as 0 to 255, so e.g. 50 lx was reported as 19.6 lx. It is now read as 0 to 100 lx; the high range is unchanged. Contributed by eltakoal (#14).
- **A cover reported `stopped` about 1.5 s after it had reported `open` or `closed`** (`D2-05-xx`): the watchdog that reports `stopped` when no position telegram arrives during a movement was cancelled only at `stopped`, so a fully open or closed cover ended up as stopped. It is now cancelled at an end position as well. Contributed by eltakoal (#15).

## [0.18.1] — 2026-11-25

### New features
- **Water sensors: `A5-30-01`, `A5-30-03` and `F6-05-01`**, with variants for the Eltako FSM60B with the water probe FWS60 (`A5-30-03.ELTAKO.FSM60B`, its factory setting, and `A5-30-01.ELTAKO.FSM60B`) and the Eltako FWS81 (`F6-05-01.ELTAKO`). New observables `water_detected` and `battery_low`. For `A5-30-01.ELTAKO.FSM60B`, "contact closed" is taken as water; this is not yet confirmed on a device. An `EEPDataField` can now lie in the status byte of a telegram (`in_status=True`); such a field is only decoded (see `docs/IMPLEMENT_EEP.md`). Contributed by eltakoal (#11).

### Bug fixes
- **A telegram that differed from the previous one only in its status byte was dropped as a repeated copy**: e.g. the FWS81 sends water and no water with the same data byte and tells them apart by the NU bit of the status byte. The repeat filter now also compares the status byte, without its repeater count. Contributed by eltakoal (#11).
- **A 4BS teach-in with the base EEP of a registered variant replaced the variant**: e.g. an FSM60B registered as `A5-30-03.ELTAKO.FSM60B` became a plain `A5-30-03` when it was taught in again. A variant is never sent over the air, so such a teach-in now keeps the registered variant. Contributed by eltakoal (#11).
- **Sender-addressed devices taught in by the gateway shared one sender** (#4): a device added with `add_device()` without a sender, such as an Eltako FSB61 shutter actuator, was given the default sender BaseID+0, and so was every other one. The learn telegram (`LearnTelegram`) then taught each of them BaseID+0, and a command to one of them moved all of them. Such a device now has no sender slot until the gateway teaches it in: the learn telegram assigns it the lowest free slot (BaseID+1…+127), as `docs/TEACHIN.md` describes for sender-addressed devices. Until then, commands to it are still sent from BaseID+0, so a device taught in by an earlier version keeps working. An integration must persist the assigned slot (read it from `gateway.sender_slots` after the learn telegram). A device that is taught in again still reacts to BaseID+0 until this sender is deleted from it (Eltako: rotary switch at `CLR`), see `docs/TEACHIN.md`.

## [0.18.0] — 2026-11-24

### Breaking changes
- **Two-state values are reported as booleans**: `motion`, `occupancy_button`, `day_night`, `contact_state` and the D2-01 `error_level` are observables of kind `BINARY`, but their value was the text of the field's enumeration, e.g. `"no motion"`. A text counts as true whatever it says, so a consumer reading the value as a boolean saw such an entity as always on. They are now `bool`: `True` means motion detected, button pressed (occupied for `A5-10-23`), day, contact open, and a hardware warning or failure. Consumers that compared these values with the texts must compare with `True`/`False`. The text is still available in `EEPMessage.decoded`. A raw value the enumeration does not list gives no value, as does "not supported" for the D2-01 error level. For new profiles, `EEPDataField` has the new `true_values` and `false_values`; a test fails for a `BINARY` field without `true_values` (see `docs/IMPLEMENT_EEP.md`). Contributed by eltakoal (#10).

### New features
- **`D5-00-01` support (single input contact, 1BS)**, e.g. the NodOn SDO-2-1-05 door/window contact sensor: reports `contact_state` (`True` when open). Contributed by dakonu (#5).
- **A device may have a base address**: `Gateway.add_device()` and `Device.address` are now documented and typed to take a `BaseAddress` as well as an `EURID`, and a test covers decoding such a device. This is the case for a device another gateway speaks for, e.g. an actuator on a wired bus whose telegrams the bus gateway sends under its base address range. Contributed by eltakoal (#7).
- **`DeviceAddress` type**: `EURID | BaseAddress`, exported from the package. All gateway methods and callbacks which take or return the address of a device use it: `add_device()`, `remove_device()`, `device_spec()`, `device_specs`, `set_device_config()`, `send_command(destination=...)`, `start_learning(for_device=...)`, `ToggleLearning(for_device=...)`, `sender_slots`, `learning_sender_options()`, the new-device and device-taught-in callbacks, and `Observation.device`. Previously most of them were typed `EURID` only, although a device may send under a base address (see above). No change in behaviour.

### Bug fixes
- **4BS re-teach-in with another EEP was not reported**: if a registered device was taught in again with a different EEP, the gateway updated its registration but did not call the device-taught-in callbacks, so an integration kept the old device type. The callbacks are now called for such a re-teach-in as well. A re-teach-in with the same EEP is still ignored. Contributed by eltakoal (#7).
- **4BS re-teach-in with another EEP kept the observers of the old EEP**: the gateway updated the device type, but the device was still decoded into observations by the observers of its previous EEP, with that EEP's config defaults. E.g. after a re-teach-in from `A5-02-05` to `A5-04-02`, humidity was never reported. The device is now set up anew for the new EEP; it keeps its name, its sender and the config values the new EEP also has.
- **The list of senders seen grew without limit**: the gateway remembers every sender it has received a telegram from, so that `add_new_device_callback` is called only once per sender, and never trimmed this list for senders that are not registered devices. Sender addresses are not authenticated, so a transmitter using a new sender address with every telegram, by fault or on purpose, made the process grow for as long as the gateway lived. At most `MAX_KNOWN_SENDERS` (4096) such senders are now remembered, the one seen first is forgotten first; a forgotten sender that sends again is reported by `add_new_device_callback` as new again. Registered devices are not affected. Contributed by eltakoal (#9).

### Internal / maintenance
- Dev tools (ruff, pytest, pytest-asyncio, pre-commit, bump-my-version) are now declared as the `dev` extra in `pyproject.toml` and installed by `scripts/setup.sh`. Ruff is pinned to 0.17.6, and pre-commit and CI both use this version: an unpinned newer ruff in CI sorted imports differently than the local one. Ruff now also checks E402 (imports not at the top of a module).

## [0.17.0] — 2026-11-22

ESP2 support and the related changes in this release were contributed by eltakoal (#6).

### Breaking changes
- **`VersionInfo.eurid` and `Gateway.eurid` can be `None` after `start()`**: their type changed from `EURID` to `EURID | None`, because a module which speaks ESP2 does not report its EURID. For ESP3 modules both are set as before. Code which uses `gateway.eurid` to identify the gateway device — e.g. as a device ID in an integration — should use the new `Gateway.device_address` instead: it is the EURID for ESP3 modules and the base ID for ESP2 modules, and it is the `device` of the gateway's own observations. Type checkers will flag uses which assume `eurid` is always set.

### New features
- **`D2-05-01` support (4-channel blinds control)**: previously only `D2-05-00` (1 channel) was implemented. Multi-channel devices get one `chN_cover` entity per channel (`ch1_cover`…`ch4_cover`), each backed by its own `CoverObserver` instance with independent position/cover-state/watchdog tracking and CHN-based filtering, so channels never interfere with each other.
- **`D2-05-02` support (1 channel, reduced command set)**: same wire format as `D2-05-00` for CMD 1–4, without CMD 5 (Set parameters) or alarm-mode support, per the EEP spec's family table.
- **CMD 5 "Set parameters" support for `D2-05-00`/`D2-05-01`**: new `CoverSetParameters` instruction (`Instructable.COVER_SET_PARAMETERS`) configures an actuator's vertical run time, rotation time, and alarm action.
- `enocean_async/eep/d2/d2_05_00.py` consolidated into `enocean_async/eep/d2/d2_05.py`, covering all three TYPE variants via a shared `_spec()` factory — matching the file-per-family convention already used by `d2_01.py`.
- **ESP2 module support (e.g. Eltako FAM-USB)**: `Gateway(port, protocol=SerialProtocol.ESP2)` connects to a module which speaks the EnOcean Serial Protocol Version 2. The new `protocol/esp2/` layer (`ESP2Packet`, `EnOceanSerialProtocol2`) translates between ESP2 frames and ESP3 packets at the serial layer, so everything above it is unchanged: received RPS/1BS/4BS telegrams become `RADIO_ERP1` packets, answers of the module become `RESPONSE` packets, and outgoing `RADIO_ERP1` packets and the read-base-ID/read-version commands are sent as ESP2 frames. Limitations of ESP2: only RPS, 1BS and 4BS telegrams (sending anything else raises `ValueError`); no RSSI, destination address or security level; the base ID cannot be changed.
- **`Gateway.device_address`**: the address that identifies the gateway itself, e.g. as `device` of its own observations — the EURID of the module or, for a module which does not report its EURID (ESP2), its base ID. `Gateway.eurid` and `VersionInfo.eurid` are `None` for such a module, and it has no `"eurid"` sender slot: the `sender_slot`, `learning_sender` and `default_sender` choices omit `"eurid"`, and setting it raises `ValueError`.
- `Gateway(port, baudrate=None, protocol=SerialProtocol.ESP3)`: the baudrate now defaults to the one the serial protocol specifies (57600 for ESP3 as before, 9600 for ESP2). New `Gateway.serial_protocol` property; `SerialProtocol` is exported from the package.
- `examples/serial_monitor.py` takes the serial protocol as optional second argument (`esp3` or `esp2`).

### Bug fixes
- **`telegrams_sent` counted telegrams which were never sent**: `send_command()` incremented the counter before sending, so a command which failed — e.g. a VLD command for an ESP2 module, or any command while disconnected — was still counted. The counter now increments in `send_esp3_packet()` once a radio telegram has actually been written to the module. As a consequence, teach-in responses and radio telegrams sent directly via `send_esp3_packet()` are now counted as well, matching `telegrams_received`, which counts every received telegram.
- **Serial port could still be in use right after `stop()` or a failed `start()`**: the serial connection is closed in the background, so opening the same port again right away — e.g. to try another serial protocol — could fail with "Device or resource busy". `stop()` and a failed `start()` now wait until the port is released, for at most one second: a port whose pending output cannot be sent is only released by the operating system much later.
- **4BS teach-in ignored devices whose manufacturer-specific EEP is not implemented**: a 4BS teach-in telegram carries the manufacturer ID, and the gateway looked up the EEP for exactly that manufacturer (e.g. `A5-04-02.ELTAKO`). If only the generic EEP (`A5-04-02`) is implemented, the device was rejected as "not supported". The gateway now falls back to the generic EEP, as it already does for UTE teach-in. The teach-in response still echoes the EEP and manufacturer ID of the query.
- **Multi-channel commands could silently target "all channels" instead of the intended one**: `SetSwitchOutput`/`QueryActuatorStatus`/`QueryActuatorMeasurement` (`D2-01`) and the `Cover*` instructions (`D2-05`) only recognized a bare digit string (e.g. `"2"`) as `entity_id`, requiring the raw channel index rather than the actual entity catalog id. Passing the catalog id (`"ch2_switch_state"`, `"ch2_cover"`, as returned by the entity list) failed the digit check and fell back to "all channels"/"all output channels" , causing every channel to react to a single-channel command. Fixed with a shared `channel_from_entity_id()` helper (`enocean_async/eep/d2/_util.py`) that correctly parses the `"ch<N>_<suffix>"` catalog id format.

### Internal / maintenance
- `examples/serial_monitor.py` now awaits `gateway.stop()` on Ctrl+C; before, the gateway was never actually stopped.
- README: the send-pipeline example used instruction names which no longer exist (`SetCoverPosition`, `StopCover`) and a wrong `SetSwitchOutput` argument.

## [0.16.0] — 2026-05-28

### Breaking changes
- **`A5-38-08` config key `dimming_mode` replaced by `dimming_range`**: the generic EEP profile now uses `dimming_range` (`"relative"` / `"absolute"`) to reflect that the choice is purely about the EDIM encoding. Any device config persisting `"dimming_mode"` for a generic `A5-38-08` device must be migrated to `"dimming_range"`.
- **`A5-38-08.ELTAKO` config key `dimming_mode` replaced by `ramp_mode`**: the Eltako profile now uses `ramp_mode` (`"hardware"` / `"software"`) to reflect that the choice controls who owns the ramp speed — the device's own hardware setting or the telegram's RMP field. Any device config persisting `"dimming_mode"` for an Eltako device must be migrated to `"ramp_mode"`.

### Bug fixes
- **Eltako FUD/FLD dimmers always dimmed at hardware speed**: `RMP=0x00` was sent by default (via `ramp_time=0`), but for Eltako devices `RMP=0x00` means "use the device's internally configured ramp speed", not "immediate". The Eltako-specific encoder now defaults to `ramp_time=1` (fastest software-controlled speed) with a valid range of 1–255. `RMP=0x00` is only sent in `ramp_mode="hardware"`.
- **`dim_value=0` incorrectly mapped to `min_brightness` for Eltako**: when `min_brightness > 0`, `CentralDim(dim_value=0)` was encoding `EDIM=min_brightness` rather than `EDIM=0`. Turning off via a dim-to-zero command now always sends `EDIM=0` regardless of the `min_brightness` setting.

### New features
- **`CentralDimOff` instruction for Eltako dimmers**: a new instruction that sends the exact Eltako switch-off telegram (`0x02, 0x00, 0x00, 0x08`). Per the Eltako protocol, `DB2`/`DB1` are wildcards when `SW=0`; the device always uses its own hardware-configured ramp speed for switch-off regardless of RMP. `CentralDimOff` is exposed in `_ELTAKO_DIMMER_ENTITY`'s actions alongside `CentralDim`, replacing `CentralSwitch` for Eltako.
- **Two new diagnostic entities for `A5-38-08.ELTAKO`**:
  - `dimmer_state` — binary sensor reporting the `SW` bit from received dimming telegrams (`Observable.SWITCH_STATE`).
  - `dimmer_output` — scalar sensor reporting the raw `EDIM` value (0–100 %) as received from the device, before inverse brightness scaling (`Observable.DIMMER_OUTPUT`).
- **New `Observable.DIMMER_OUTPUT`**: raw device brightness percentage (0–100 %) distinct from `OUTPUT_VALUE`, which is scaled by `min_brightness`/`max_brightness`.

### Internal / maintenance
- **Separate Eltako dim encoder**: `EEP_A5_38_08_ELTAKO` now uses a dedicated `_encode_eltako_central_dim` instead of the generic one. Eltako specifics: EDIM always 0–100 %, EDIMR always 0 (repurposed as lock bit in Eltako protocol), `SW` always 1 for `CentralDim`.
- **Separate Eltako EDIM resolver**: `_resolve_eltako_edim` always treats EDIM as 0–100 % without branching on EDIMR. The shared `_edim_to_value` helper is used by both generic and Eltako resolvers.

## [0.15.0] — 2026-05-17

### Breaking changes
- **`is_eurid()`, `is_base_address()`, `is_broadcast()` converted to properties**: callers must drop the parentheses (`addr.is_eurid` instead of `addr.is_eurid()`).

### New features
- **Identification log on startup**: `Gateway.__init__` now emits an `INFO` log line `"enocean-async vX.Y.Z Gateway init on <port>."` as its very first log message, making the library version immediately visible in application logs.
- **Gateway `default_sender` config**: a new gateway config key `"default_sender"` (options: `"auto"`, `"0"`–`"127"`, `"eurid"`; default: `"auto"`) controls which sender slot is used when a device is registered via `add_device()` without an explicit `sender` argument, and as the backfill sender in `send_command()` when `device.sender` is unset. `"auto"` preserves the previous behaviour (BaseID+0). Set via `gateway.set_gateway_config("default_sender", "1")`. A matching `default_sender` entity is exposed in `gateway_entities` for UI configuration.

## [0.14.0] — 2026-05-16

### Breaking changes
- **`stop()` is now `async`**: callers must `await gateway.stop()`. This was necessary to correctly await the reconnect task and background tasks before returning.

### Bug fixes
- **`stop()` now properly awaits the reconnect task**: previously `stop()` only called `task.cancel()` without awaiting, so the reconnect task could complete `start()` (opening the serial port) after `stop()` returned, leaving the port open. `stop()` now cancels the task and awaits it, then re-asserts `__stopped = True` to handle the case where `start()` ran to completion inside the reconnect task before the cancellation arrived.
- **`stop()` now properly awaits background tasks**: teach-in response tasks were cancelled but not awaited, so they could still attempt to write to the transport after it was closed. `stop()` now uses `asyncio.gather(..., return_exceptions=True)` to wait for all background tasks to finish before closing the transport.
- **Double reconnect task on `start()` failure during reconnect**: when `start()` failed during a reconnect attempt and closed the transport, `connection_lost` fired with `__stopped = False` and spawned a second `__try_to_reconnect` task alongside the one already running. Fixed by introducing `__disconnect()` which sets `__stopped = True` before closing the transport, preventing `connection_lost` from treating a deliberate close as an unexpected disconnect.
- **`stop()` now cancels an in-flight `__send_future`**: if `send_esp3_packet()` was awaiting a response when `stop()` was called, the future was left pending until the 500 ms timeout. `stop()` now cancels it immediately.
- **`fetch_base_id()` and `fetch_version_info()` now raise on failure**: both methods previously returned `None` on timeout, bad response code, or short response data, while `start()` only checked for exceptions — so a silent `None` return would let `start()` complete with no base ID or version info set. Both methods now raise `ConnectionError` in all failure cases; return types narrowed from `… | None` to `BaseAddress` and `VersionInfo` respectively.

### Internal / maintenance
- **Exponential backoff in reconnect**: `__try_to_reconnect` previously waited a fixed 5 s between all 720 attempts (1 hour cap). It now uses exponential backoff starting at 2 s, doubling each failure up to a 300 s maximum, and retries indefinitely.
- **Log level corrections**: `start()` failure logs downgraded from `error` to `warning` (transient during reconnect); individual reconnect attempt failures downgraded from `warning` to `debug`; failed UTE/4BS teach-in response sends downgraded from `error` to `warning`; "cannot send: not connected" downgraded from `error` to `warning`.
- **Removed log-before-raise pattern**: redundant `logger.warning/error` calls immediately before `raise ValueError` removed from `send_command()` and `add_device()` — the exception is the error signal.

## [0.13.5] — 2026-04-19

### New features
- **Echo filter**: the gateway now detects and drops its own packets echoed back by repeaters. Sent RADIO_ERP1 packets are fingerprinted (`RORG + telegram_data + sender`) and cached for 2 seconds (ring buffer, max 32 entries). On receive, if the fingerprint matches a recently sent packet, the telegram is silently dropped with a debug log entry. This prevents the gateway from processing its own commands as if they were incoming device telegrams.
- **Repeat filter**: the gateway now detects and drops repeated copies of device telegrams relayed by repeaters. When an original telegram (`repeater_count` = `Original` or `ShallNotBeRepeated`) is received, its fingerprint is cached for 2 seconds (ring buffer, max 64 entries) and the `repeater_count` check is made at the call site in `__process_erp1_telegram`. If a subsequent telegram with `repeater_count > 0` carries the same fingerprint, it is dropped with a debug log entry. If the original was never received (lost in RF noise), the first repeated copy passes through normally.


## [0.13.4] — 2026-04-19

### Internal / maintenance
- **Relaxed `serialx` version constraint from `==1.2.3` to `>=1.2.2`** to allow use alongside other packages (e.g. Home Assistant) that may pin a compatible version.

## [0.13.3] — 2026-04-19

### New Features
- **`LEARN_TELEGRAM` now allocates a free sender slot for sender-addressed devices**: previously, if a device was added via `add_device()` without an explicit `sender`, sending a learn telegram always used BaseID+0 regardless of EEP type. For sender-addressed EEPs (`uses_addressed_sending=False`), the gateway now calls `__next_available_sender()` to allocate a free BaseID+n slot, persists it on `device.sender` and `device.config["sender_slot"]`.

### Bug fixes
- **A5-38-08 CMD=2 (Dimming) status telegrams silently dropped**: `EDIM` field had `scale_min_fn=lambda _: None`, causing a `TypeError` in `bitstring_scaled_value()` on every incoming dimming status telegram. The exception was swallowed by the gateway, so `OUTPUT_VALUE` was never updated from device feedback. Fixed to `0.0` (the semantic resolver overrides the value anyway).
- **UTE teach-in success log showed gateway address instead of device address**: `response.sender` (the gateway's own sender slot) was logged as "device"; corrected to `response.destination`.
- **4BS re-teach-in crash when `device.sender` is `None`**: `response_for_query()` was called with `existing.sender` directly; if the device had been added before `start()` (base ID not yet available), this is `None`, leading to `AttributeError` in `to_esp3()`. Now falls back to `__sender_id_for_learning` or `__base_id`.
- **`MetaDataObserver` constructor parameter name mismatch**: `__init__` used `on_state_change` while the parent `Observer` dataclass field is `on_observation`; the callback was stored correctly (passed positionally) but the keyword argument in `gateway.add_device()` used the wrong name. Both renamed to `on_observation`.
- **UTE re-teach-in incorrectly fired `DeviceTaughtInCallback` and logged "successfully registered"**: the log line and callback were outside the `if existing is None:` guard, so they fired even for re-teach-ins of already-registered devices.
- **`LEARN_TELEGRAM` always used BaseID+0 for sender-addressed devices**: when `device.sender` was unset (device added via `add_device()` without explicit sender), the LEARN_TELEGRAM path fell back to `self.base_id` regardless of EEP type. For sender-addressed EEPs (`uses_addressed_sending=False`) the gateway now allocates the next free BaseID+n slot, persists it on `device.sender` and `device.config["sender_slot"]`, so the Eltako device learns a unique sender address rather than the shared BaseID+0.
- **`start_learning()` left gateway in broken state on invalid `sender_id`**: state mutations (`__is_learning`, `__allow_teach_out`, `__focus_device`) happened before the `sender_id` validity check, so a `ValueError` left the gateway with `__is_learning=True` but no timeout task or deadline. Validation now runs first.
- **`asyncio.get_event_loop()` replaced with `get_running_loop()`** in `start_learning()` and `__tick_learning_remaining()`.
- **Learning mode is now stopped on disconnect**: previously, `stop_learning()` was not called from `connection_lost()`, so the learning window remained nominally active (countdown ticking, `learning_active=True`) while the gateway was disconnected or reconnecting — a state in which no teach-in telegrams can be received. Learning mode is now cancelled immediately on any disconnect; the user must re-trigger it after reconnection.


### Internal / maintenance
- **`remove_device()` now clears the sender from `__known_senders`**: previously, removing a device left its EURID in the internal seen-senders set, suppressing future `NewDeviceCallback` notifications for that address.
- **`__known_senders` changed from `list` to `set`**: membership test runs on every received telegram; `set` gives O(1) lookup vs. O(n) for `list`.
- **`Address.__eq__` returns `NotImplemented` for non-`Address` types** instead of raising `TypeError`.
- **`CommonCommandTelegram.optional_data` default corrected** from `None` (wrong type) to `b""`; removed now-redundant `__post_init__` null-check.
- **`stop_learning()` is now a no-op when learning is not active**, preventing a spurious "Learning mode stopped" log entry on every disconnect.
- **`send_esp3_packet()`: send callbacks now fire after the serial write**, not before; debug log moved to pre-write position.
- Minor: removed dead `hasattr` check in `gateway_command()`; removed trailing `continue` in reconnect loop; `Optional[X]` → `X | None` in `SendResult`; `bytes +=` chain in `ERP1Telegram.to_esp3()` replaced with a single concatenation expression.

### Other
- Double space removed from 4BS teach-in response log string.

## [0.13.2] — 2026-04-18

### Internal / maintenance
- **Switched serial backend from `pyserial-asyncio-fast` to `serialx==1.2.3`**: no public API changes; `gateway.py` and `protocol/esp3/protocol.py` updated to import `serialx` directly.

## [0.13.1] — 2026-04-12

### Bug fixes
- **`SemanticResolver` signature mismatch in six EEP modules**: resolvers in `a5_06.py` (`_a5_06_illumination_resolver`, `_a5_06_eltako_illumination_resolver`) and `d2_01.py` (`_resolve_switch_state`, `_resolve_output_value`, `_resolve_energy`, `_resolve_power`) were declared with only two positional arguments `(raw, scaled)` instead of the required three `(raw, scaled, config)`, causing a `TypeError` when any of those EEPs received a telegram.

## [0.13.0] — 2026-04-11

### Breaking changes
- **`Dim` → `CentralDim`**, **`Switch` → `CentralSwitch`**, **`Instructable.DIM` → `CENTRAL_DIM`**, **`Instructable.SWITCH` → `CENTRAL_SWITCH`**: A5-38-08 lighting instructions prefixed with `Central` to reflect the "central command gateway" profile and avoid confusion with D2-01's `SetSwitchOutput`. Module `semantics/instructions/dimmer.py` renamed to `central_command.py`.
- **`ToggleLearning` → `LearningToggle`**, **`Instructable.TOGGLE_LEARNING` → `LEARNING_TOGGLE`**: class name, instructable constant, and entity id `learning_toggle` now all use the same noun-first word order.
- **`TeachIn` → `LearnTelegram`**, **`Instructable.TEACH_IN` → `LEARN_TELEGRAM`**: renamed to match Eltako documentation terminology. Module `semantics/instructions/teach_in.py` renamed to `learn_telegram.py`.
- **`EEPSpecification.teach_in_payload` → `learn_telegram_payload`**: field renamed to match the instruction rename.
- **`start_learning(focus_device=...)` → `start_learning(for_device=...)`**: parameter renamed to align with `LearningToggle.for_device`.

### Bug fixes
- **A5-7F-3F FSB open/close commands raised `ValueError: Unknown telegram type`**: the open and close encoders used `EEPMessageType(id=1)` / `id=2)`, treating the message type ID as a semantic command selector. For `SimpleProfileSpecification` the ID is a telegram-definition lookup key and only `0` is valid. Fixed by setting `id=0` in all three encoders; the `DIR` field already encodes the direction distinction.

## [0.12.7] — 2026-04-05

### New features
- **`ToggleLearning` instruction + `Instructable.TOGGLE_LEARNING`**: new `ToggleLearning()` command to start/stop gateway learning mode from the instruction pipeline. When `for_device: EURID | None` is set, the gateway enters **focused learning mode** — UTE and 4BS teach-in telegrams from any EURID other than `for_device` are silently ignored during the window, preventing accidental registration of other devices. Exported from the top-level package.
- **`DeviceSpec.gateway_entities`**: second entity list on `DeviceSpec` for entities that are sourced from the **gateway device** but rendered on the device's config page. The integration observes and commands these via the gateway's EURID. Currently populated with `learning_toggle` and `learning_remaining` for sender-addressed devices that have no fixed `teach_in_payload` (i.e. require the gateway to listen for an inbound teach-in from the device).
- **`sender_slot` entity injected for all devices**: `device_spec()` now always appends a `sender_slot` `CONFIG_ENUM` entity (options: `"auto"`, `"0"`–`"127"`, `"eurid"`; default `"auto"`) to `DeviceSpec.entities`. Setting it via `set_device_config(address, "sender_slot", value)` immediately updates `device.sender`; a collision check raises `ValueError` if the target slot is already in use by another device. The initial value is seeded at `add_device()` time from the device's current sender address.
- **Gateway learning-mode entities**: five new entities added to `gateway.gateway_entities`:
  - `learning_active` — `Observable.LEARNING_ACTIVE` (bool); `True` while a learning session is open
  - `learning_remaining` — `Observable.LEARNING_REMAINING` (seconds); counts down from the timeout once per second via `loop.call_later()`
  - `learning_toggle` — trigger entity accepting `Instructable.TOGGLE_LEARNING`
  - `learning_timeout` — `CONFIG_NUMBER` controlling the default learning window length (seconds)
  - `learning_sender` — `CONFIG_ENUM` selecting which sender slot the gateway uses when responding during teach-in
- **Focused learning mode**: `start_learning(focus_device: EURID | None = None)` — when `focus_device` is set, the UTE and 4BS handlers reject telegrams from any other EURID before processing them. `stop_learning()` clears the focus. Allows integrations to retrigger teach-in for a specific device from the device's config page without the risk of registering an unrelated device.
- **`Observable.LEARNING_ACTIVE`** (bool) and **`Observable.LEARNING_REMAINING`** (seconds) added.

## [0.12.6] — 2026-04-01

### New features
- **`INSTRUCTION_FOR: dict[Instructable, type[Instruction]]`**: library-maintained mapping from every `Instructable` constant to its `Instruction` subclass. Integrations can use this instead of maintaining their own map, eliminating silent gaps when new instructables are added. Exported from the top-level package.

## [0.12.5] — 2026-04-01

### New features
- **`TeachIn` instruction**: new `TeachIn()` command for sender-addressed Eltako devices (FSB shutters, FUD/FSR dimmers/relays). After `add_device()`, call `await gateway.send_command(address, TeachIn())` to register the gateway's sender slot with the device. Exported from the top-level package.
- **`Instructable.TEACH_IN`**: new `"teach_in"` instructable constant.
- **`EEPSpecification.teach_in_payload: bytes | None`**: fixed 4-byte learn telegram payload on specs that require it. The gateway bypasses `EEPHandler.encode()` for `TEACH_IN` and sends the payload directly as a 4BS ERP1 telegram.
- **`EEP.variant` field**: new optional `variant: str | None` parameter on `EEP` for manufacturer-specific profile disambiguation where the same EEP bytes are reused for incompatible payloads. String form: `"A5-7F-3F.ELTAKO.FSB"`; `DeviceType` ID: `"ELTAKO/A5-7F-3F/FSB"`. Variant is a registration-time discriminator — never carried on the wire.
- **`EEP_A5_7F_3F_ELTAKO_FSB`**: full spec for Eltako FSB14/FSB61/FSB71 roller-shutter actuator (`A5-7F-3F.ELTAKO.FSB`). Covers stop/open/close commands with configurable travel time, cover state decoding from completed-movement telegrams, and teach-in support.
- **`EEP_A5_38_08_ELTAKO`**: new Eltako-specific variant of A5-38-08 (`A5-38-08.ELTAKO`) for FUD/FSR sender-addressed dimmers and relays. Identical to `EEP_A5_38_08` but adds `teach_in_payload` and a `teach_in` config entity. Eltako device type entries (`FUD61NPN`, `FLD61`) updated to reference this variant.
- **`Instruction.action` declared in base class**: `ClassVar[Instructable]` contract is now part of `Instruction` itself, enabling correct typing wherever `command: Instruction` is used.
- **`EEP.__hash__` / `__eq__` include `variant`**: `EEP("A5-7F-3F.ELTAKO")` and `EEP("A5-7F-3F.ELTAKO.FSB")` are now different keys. Existing EEPs without a variant (`variant=None`) are unaffected.
- **`EEP_A5_7F_3F_ELTAKO` renamed to `EEP_A5_7F_3F_ELTAKO_FSB`**.


## [0.12.4] — 2026-03-30

### Bug fixes
- **`Address` string parsing rejects malformed parts**: each colon-separated part must now be exactly 2 hex characters; previously a 3-digit part (e.g. `"01:AAA:BB:CC"`) was silently truncated to a wrong integer value.

## [0.12.3] — 2026-03-30

### New features
- **`Gateway.is_connected` property**: new read-only boolean property for direct connection-status polling, complementing the existing observer pattern.

### Improvements
- **`connection_status` gateway entity** now carries `EntityCategory.DIAGNOSTIC`.
- **EEP implementation guide** added at `docs/IMPLEMENT_EEP.md`.

## [0.12.2] - 2026-03-29

### Improvements
- **`Observable` member type annotations added**: added type annotations to `name`, `kind`, `unit`, and `possible_values`.

## [0.12.1] — 2026-03-29

### Bug fixes
- **ESP3 protocol buffer always advanced past processed frames**: packet creation (`ESP3PacketType(packet_type)`) and gateway dispatch (`process_esp3_packet`) are now wrapped in `try/except/finally` so `del buffer[:total_len]` runs unconditionally. Previously, an unknown packet-type byte would raise `ValueError` before the buffer was consumed, causing the same frame to be re-parsed in an infinite loop (fixes [#2](https://github.com/henningkerstan/enocean-async/issues/2)).
- **4BS teach-in tolerates unknown manufacturer IDs**: `Manufacturer.from_id()` is now wrapped in `try/except ValueError` so unrecognized manufacturer codes fall back to `Manufacturer.RESERVED` instead of raising an exception.

## [0.12.0] — 2026-03-25

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
