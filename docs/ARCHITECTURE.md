# Architecture

<!-- This file documents the architecture of the enocean-async library. -->

## Overview

`enocean-async` is an asyncio-based Python library for communicating with EnOcean devices over an EnOcean USB gateway. The library has two symmetric pipelines:

- **Observable pipeline** (receive): raw radio telegrams → typed `Observation` objects carrying entity state updates like `entity_id="temperature", values={TEMPERATURE: 21.3}`.
- **Instruction pipeline** (send): typed `Instruction` subclasses carrying `entity_id` and action-specific parameters → encoded `ERP1Telegram` → radio signal, e.g. `CoverSetPositionAndAngle(entity_id="cover", position=64)` or `CoverStop(entity_id="cover")`.

Each pipeline layers protocol detail away from the application. The gateway orchestrates both.

---

## Address model

All 32-bit EnOcean addresses are represented by the `Address` class and its three subclasses in `address.py`. The constructor accepts an `int`, a colon-separated hex string (`"AB:CD:EF:01"`), or a 4-byte sequence (`bytes`, `bytearray`, `list[int]`). Use `int(addr)` / `str(addr)` for numeric / string conversion; `addr.bytelist` for the big-endian byte list.

| Class | Range | Role |
|---|---|---|
| `EURID` | `00:00:00:00` – `FF:7F:FF:FF` | Permanent chip ID of a device |
| `BaseAddress` | `FF:80:00:00` – `FF:FF:FF:FE` | Gateway base ID and its 128 sender slots (BaseID+0…+127) |
| `BroadcastAddress` | `FF:FF:FF:FF` | Broadcast destination |

`SenderAddress = EURID | BaseAddress` — the union of all addresses that may appear as the sender of a telegram.

---

## Entities, Observables, and Instructables

These three concepts form the semantic vocabulary of the library.

### Entities

An **entity** is a physical real-world thing within a device — a push button, a cover motor, a relay channel, a temperature sensor. It is the primary unit of identity in the library.

Entities are declared statically in the EEP specification, since the EEP fully defines what physical sub-units a device has. Each entity has:

- A stable string **id** within the device (e.g. `"a0"` for a rocker button, `"cover"` for a cover motor, `"0"` for relay channel 0, `"temperature"` for a temperature sensor).
- A set of **observables** — the quantities this entity reports.
- A set of **instructables** — the commands this entity accepts.

```python
@dataclass(frozen=True)
class Entity:
    id: str
    observables: frozenset[Observable]
    actions: frozenset[Instructable] = frozenset()
```

Examples as declared in EEP files:

```python
# F6-02: four single-rocker entities
# Simultaneous two-button presses (SA=1) fire two atomic events with the same timestamp.
Entity(id="a0", observables=frozenset({BUTTON_EVENT}))
Entity(id="b0", observables=frozenset({BUTTON_EVENT}))
Entity(id="a1", observables=frozenset({BUTTON_EVENT}))  
Entity(id="b1", observables=frozenset({BUTTON_EVENT}))  

# A5-04: two independent sensor entities (separate concerns)
Entity(id="temperature", observables=frozenset({TEMPERATURE}))
Entity(id="humidity",    observables=frozenset({HUMIDITY}))

# D2-05: one cover entity, multiple observables (all describe the same physical thing)
Entity(
    id="cover",
    observables=frozenset({COVER_STATE, POSITION, ANGLE}),
    actions=frozenset({COVER_SET_POSITION_AND_ANGLE, COVER_STOP, COVER_QUERY_POSITION_AND_ANGLE, COVER_OPEN, COVER_CLOSE}),
)

# D2-01-07: one relay channel with metering — one entity per observable
Entity(id="ch1_switch_state", observables=frozenset({SWITCH_STATE}),
       actions=frozenset({SET_SWITCH_OUTPUT, QUERY_ACTUATOR_STATUS, QUERY_ACTUATOR_MEASUREMENT}))
Entity(id="ch1_error_level",  observables=frozenset({ERROR_LEVEL}))
Entity(id="ch1_energy",       observables=frozenset({ENERGY}))
Entity(id="ch1_power",        observables=frozenset({POWER}))
```

The principle for grouping observables into entities: multiple observables belong to the same entity when they describe the **same physical thing** and must be handled as one unit by the consumer (cover POSITION, ANGLE, COVER_STATE are all facets of one cover motor — a HA `CoverEntity` needs all three at once). Observables belong to separate entities when they are independently meaningful with separate real-world identities (temperature and humidity are separate physical quantities).

A fully unique physical thing in the system is the pair `(device_address, entity_id)`.

### Observables

An **observable** is a quantity that an entity reports. It has four intrinsic properties:

- A **unique name** — what it is observing (e.g. `"temperature"`, `"switch_state"`, `"button_event"`). This is also the string value of the enum member.
- A **native unit** — the one canonical physical unit for that quantity (`None` for dimensionless or categorical values).
- A **kind** (`ValueKind.SCALAR`, `BINARY`, or `ENUM`) — the nature of the value.
- **`possible_values: list[str] | None`** — for `ENUM`-kinded observables, the exhaustive list of string values the observable can take; `None` for SCALAR/BINARY observables.

```python
class Observable(str, Enum):
    def __new__(cls, name: str, unit: str | None = None,
                kind: ValueKind = SCALAR, possible_values: list[str] | None = None):
        obj = str.__new__(cls, name)
        obj._value_ = name
        obj.unit = unit
        obj.kind = kind
        obj.possible_values = possible_values
        return obj

    TEMPERATURE   = ("temperature",   "°C",  SCALAR)
    HUMIDITY      = ("humidity",      "%",   SCALAR)
    ILLUMINATION  = ("illumination",  "lx",  SCALAR)
    SWITCH_STATE  = ("switch_state",  None,  BINARY)
    BUTTON_EVENT  = ("button_event",  None,  ENUM,   ["pressed", "clicked", "held", "released"])
    POSITION      = ("position",      "%",   SCALAR)
    COVER_STATE   = ("cover_state",   None,  ENUM,   ["open", "opening", "closed", "closing", "stopped"])
    WINDOW_STATE  = ("window_state",  None,  ENUM,   ["open", "tilted", "closed"])
    # Metering
    ENERGY        = ("energy",        "Wh",  SCALAR)
    POWER         = ("power",         "W",   SCALAR)
    ...
```

The `str, Enum` pattern makes each member both an `Observable` instance and a plain `str`, preserving dict-key and equality semantics. The unit is fixed per observable type — if two quantities differ in unit, they are different observables (e.g. `POWER = "W"` and `ENERGY = "Wh"` are separate members). `possible_values` is the authoritative source for the allowed string values of ENUM-kinded observables — populated directly on the `Observable` member rather than on `Entity`, so that any consumer (observer, integration, documentation generator) can read them without a device context.

Observable names are **semantic, not unit-encoding**. The name says *what* is being observed (`TEMPERATURE`, `POWER`), not *how* it is expressed. The unit is available as `Observable.TEMPERATURE.unit`.

An observable update is delivered as part of an `Observation` (see below).

### Instructables

An **instructable** is a category of command sent _to_ a device — telling a cover to move, a relay to switch, a dimmer to change brightness. Instructables are classified by `Instructable` enum members (`semantics/instructable.py`):

```python
class Instructable(StrEnum):
    COVER_SET_POSITION_AND_ANGLE   = "cover_set_position_and_angle"
    COVER_STOP                     = "cover_stop"
    COVER_QUERY_POSITION_AND_ANGLE = "cover_query_position_and_angle"
    COVER_OPEN                     = "cover_open"
    COVER_CLOSE                    = "cover_close"
    SWITCH                         = "switch"
    DIM                            = "dim"
    SET_FAN_SPEED                  = "set_fan_speed"
    SET_SWITCH_OUTPUT              = "set_switch_output"
    QUERY_ACTUATOR_STATUS          = "query_actuator_status"
    QUERY_ACTUATOR_MEASUREMENT     = "query_actuator_measurement"
    TEACH_IN                       = "teach_in"
    TOGGLE_LEARNING                = "toggle_learning"
```

`TEACH_IN` is used by sender-addressed devices that require the gateway to announce its sender slot to the device (e.g. Eltako FSB/FUD/FSR). `TOGGLE_LEARNING` controls gateway learning mode: `ToggleLearning()` starts a new session (or stops one already in progress); `ToggleLearning(for_device=eurid)` starts a focused session that only accepts teach-in telegrams from that specific EURID.

**`INSTRUCTION_FOR: dict[Instructable, type[Instruction]]`** is a library-maintained mapping from every `Instructable` constant to its `Instruction` subclass, exported from the top-level package. Integrations can use this instead of maintaining their own map.

`Instructable` names things you _send_. `Observable` names things you _receive_. They are separate classifiers: `COVER_STOP` is an instructable with no direct observable counterpart; `COVER_SET_POSITION_AND_ANGLE` is an instructable that will eventually produce `POSITION` and `COVER_STATE` updates as the device reports back. The formal link between an instructable and the observables it affects is declared on the `Entity` — both `observables` and `actions` live together on the entity they belong to.

---

## Observation

When an observer processes a telegram and produces an update, it emits an `Observation`:

```python
@dataclass
class Observation:
    device: SenderAddress       # which device
    entity: str                 # which entity within the device
    values: dict[Observable, Any]  # all observable values reported in this telegram
    timestamp: float            # wall-clock time
    source: ObservationSource   # TELEGRAM or TIMER
```

The complete entity identity is the pair `(device, entity)`; the `entity` is only sufficient within the scope of a device. The `values` dict may be a partial update — a telegram may only carry a subset of an entity's observables (e.g. a D2-01 measurement response carries `POWER` but not `SWITCH_STATE`). The unit for any value is always `observable.unit`.

Examples:

```python
# Cover — all three observables arrive in one telegram
Observation(entity="cover", values={POSITION: 75, COVER_STATE: "open", ANGLE: 0})

# Push button — single observable entity, timer-sourced hold event
Observation(entity="a0", values={BUTTON_EVENT: "held"}, source=ObservationSource.TIMER)

# D2-01 actuator status — one entity per observable, one observation each
Observation(entity="ch1_switch_state", values={SWITCH_STATE: True})
Observation(entity="ch1_error_level",  values={ERROR_LEVEL: 0})
```

---

## Instruction

A command sent to a device is represented as a typed `Instruction` subclass:

```python
@dataclass
class Instruction:
    entity_id: str   # which entity within the device to target
    action: ClassVar[Instructable]  # declared on each subclass

@dataclass
class SetSwitchOutput(Instruction):
    action = Instructable.SET_SWITCH_OUTPUT
    output_value: int   # 0=OFF, 1–100=percentage ON

@dataclass
class CoverSetPositionAndAngle(Instruction):
    action = Instructable.COVER_SET_POSITION_AND_ANGLE
    position: int | None = None   # 0–100 %, or None to leave unchanged
    angle: int | None = None      # 0–100 %, or None to leave unchanged

@dataclass
class CoverStop(Instruction):
    action = Instructable.COVER_STOP

@dataclass
class Dim(Instruction):
    action = Instructable.DIM
    dim_value: float           # 0–100 % (percent of full brightness)
    switch_on: bool = True
    use_relative: bool | None = None   # None → use device config "dimming_mode"
    ramp_time: int | None = None       # None → use device config "ramp_time"
    store: bool | None = None          # None → use device config "store"
```

Instruction parameters are action-specific and typed — there is no generic values dict, because instruction parameters are not "things being observed." The `entity_id` targets the physical sub-unit; the typed fields provide action-specific inputs.

The gateway send method:

```python
await gateway.send_command(
    destination=device_address,
    command=CoverSetPositionAndAngle(entity_id="cover", position=64, angle=0),
)
```

---

## DeviceSpec

`DeviceSpec` (`semantics/device_spec.py`) is the setup-time description of what a device type exposes and accepts. It is built by `gateway.device_spec(address)` after calling `add_device()`, before any telegrams arrive:

```python
@dataclass
class DeviceSpec:
    device_type: DeviceType
    entities: list[Entity]
    gateway_entities: list[Entity] = field(default_factory=list)

    @property
    def eep(self) -> EEP: ...  # shortcut for device_type.eep
```

`entities` always includes entities added by the gateway regardless of EEP:

- Three **metadata** entities (`rssi`, `last_seen`, `telegram_count`)
- One **`sender_slot`** `CONFIG_ENUM` entity (options: `"auto"`, `"0"`–`"127"`, `"eurid"`). Setting this via `set_device_config(address, "sender_slot", value)` immediately updates `device.sender` and validates no collision with other devices.

`gateway_entities` holds entities that are **sourced from the gateway device** (observed/commanded via the gateway) but **rendered on the device's config page** by the integration. The gateway injects these based on device type:

| Device type | `entities` additions | `gateway_entities` |
|---|---|---|
| Destination-addressed (`uses_addressed_sending=True`) | metadata + `sender_slot` | — |
| Sender-addressed, has `teach_in_payload` (e.g. Eltako) | metadata + `sender_slot` + `teach_in` | — |
| Sender-addressed, no `teach_in_payload` | metadata + `sender_slot` | `learning_toggle`, `learning_remaining` |

An integration (e.g. Home Assistant) uses `DeviceSpec.entities` to create device-scoped platform entities, and `DeviceSpec.gateway_entities` to create gateway-sourced entities that appear on the device's config page.

---

## Receive pipeline (Observables)

```
Radio signal
    │ serial bytes
    ▼
EnOceanSerialProtocol3
    │ ESP3 framing (sync, CRC, packet type)
    ▼
ESP3Packet
    │ RADIO_ERP1 detection
    ▼
ERP1Telegram      rorg, sender EURID, raw payload bits, rssi
    │ EEP profile lookup → EEPHandler.decode()
    ▼
EEPMessage
  .raw      {field_id → int}                ← EEP spec vocabulary raw bits: "TMP", "ILL1", "R1"
  .decoded  {field_id → ValueWithContext}   ← EEP spec vocabulary decoded: "TMP", "ILL1", "R1"
  .values   {observable → ValueWithContext} ← semantic vocabulary: TEMPERATURE, ILLUMINATION
    │ Observer.decode()  (one call per observer in device.observers)
    ├── ScalarObserver(observable=TEMPERATURE) → reads values[TEMPERATURE]
    ├── ScalarObserver(observable=ILLUMINATION) → reads values[ILLUMINATION]
    ├── CoverObserver → reads values[POSITION]+values[ANGLE], infers COVER_STATE
    ├── ButtonObserver → reads raw["R1"], raw["EB"], … (raw field access)
    └── MetaDataObserver → reads rssi, generates timestamps
    │ _emit()
    ▼
Observation(device, entity, values, timestamp, source)
    │ add_observation_callback
    ▼
Application
```

The `EEPHandler` runs four passes during decode:

| Pass | Purpose |
|------|---------|
| **1 — Raw extraction** | Read every field's raw int from the telegram bitstring into a scratch dict. Done first so interdependent scale functions have full context. |
| **2 — Value decoding** | Apply enum lookup or linear scaling per field → `EEPMessage.decoded[field.id]` as `ValueWithContext(value, unit, name)`. |
| **3 — Observable propagation** | For each field with `observable` set: copy `decoded[field.id]` → `values[observable]` as `ValueWithContext`. Translates spec vocabulary to semantic vocabulary. |
| **4 — Semantic resolvers** | Run `SemanticResolver` callables that synthesise a single observable from multiple fields (e.g., A5-06: pick ILL1 or ILL2 based on range-select bit). |

Note: `EEPMessage.decoded` holds per-field `ValueWithContext` objects (decoded value + unit + name) keyed by EEP field ID. `EEPMessage.values` holds the same type keyed by `Observable` — the semantic vocabulary used by observers. Raw integer field values are in `EEPMessage.raw`.

---

## Send pipeline (Instructions)

```
Application
    │ gateway.send_command(destination, CoverSetPositionAndAngle(entity_id="cover", position=64))
    ▼
Instruction subclass instance (typed, with entity_id and validated fields)
    │ spec.encoders[command.action](command, device.config)
    ▼
RawEEPMessage
  .message_type  ← selects which telegram type to encode
  .raw           ← {field_id → int} filled in by the encoder
    │ EEPHandler.encode()
    ├── Determine data buffer size from max(field.offset+field.size) + cmd_size
    ├── Allocate zero-filled bytearray
    ├── Write CMD bits at cmd_offset/cmd_size
    └── Write each field's raw value at field.offset/field.size
    ▼
ERP1Telegram(rorg, telegram_data, sender=device.sender, destination=address)
    │ .to_esp3()
    ▼
ESP3Packet
    │ Gateway.send_esp3_packet()
    ▼
Radio signal → Device
```

---

## Layers

### 1. Serial / ESP3 Layer / ERP1 Layer

**Files:** `protocol/esp3/`, `protocol/erp1/`, `protocol/version.py`

`EnOceanSerialProtocol3` (an `asyncio.Protocol`) reassembles byte streams into `ESP3Packet` objects. The gateway routes packets by type: `RADIO_ERP1` → ERP1 processing; `RESPONSE` → matched to a pending `send_esp3_packet()` future.

`ERP1Telegram` provides bit-addressable access to the payload (`bitstring_raw_value`, `set_bitstring_raw_value`) used by both the decode and encode paths.

`protocol/erp1/ute.py` holds `UTEMessage` — parsing (`from_erp1`), response construction (`response_for_query`), and serialisation (`to_erp1`) for UTE (0xD4) teach-in/teach-out telegrams.

`protocol/erp1/fourbs.py` holds `FourBSTeachInTelegram` and its associated enums (`FourBSLearnType`, `FourBSLearnStatus`, `FourBSTeachInResult`, `FourBSEEPResult`) — parsing, response construction, and serialisation for 4BS (0xA5) teach-in telegrams.

`protocol/version.py` holds `VersionIdentifier` and `VersionInfo` — data classes for the dongle firmware version returned by the gateway's common-command query.

### 2. EEP Layer

**Files:** `eep/profile.py`, `eep/handler.py`, `eep/message.py`, `eep/a5/`, `eep/f6/`, `eep/d2/`

Every supported EEP is a module-level `EEPSpecification` (or `SimpleProfileSpecification`) instance in `EEP_SPECIFICATIONS`, keyed by `EEP` (the ID struct).

The two key types are:

- **`EEP`** (`eep/id.py`): The 4-tuple identifier — `rorg`, `func`, `type_`, optional `manufacturer`. Used as the dict key in `EEP_SPECIFICATIONS` and as a reference in `EEPMessage.eep`.
- **`EEPSpecification`** (`eep/profile.py`): The full profile — `cmd_size`, `cmd_offset`, `telegrams` dict, `semantic_resolvers`, `observers`, `encoders`, `entities`, and `uses_addressed_sending`. The simpler `SimpleProfileSpecification` is a convenience subclass for single-telegram EEPs (no CMD field; wraps datafields into a single `EEPTelegram` at key `0`).

`EEPDataField` is the atomic unit: bit offset, size, scale functions, unit function, enum map, and optional `observable` annotation that bridges the spec and semantic vocabularies.

`EEPSpecification` carries five extension points: `telegrams`, `semantic_resolvers`, `observers` (receive path behaviour), `encoders` (send path encoding), and `entities` (static declaration of physical entities).

The types referenced by `EEPSpecification` that belong conceptually to the semantics layer live in `semantics/` and are re-exported by `eep/profile.py` for convenience:
- `ObserverFactory` (`semantics/observer_factory.py`) — wraps an observer constructor callable
- `SemanticResolver`, `InstructionEncoder` (`semantics/types.py`) — type aliases for resolver and encoder callables
- `DeviceSpec` (`semantics/device_spec.py`) — setup-time description of a device's entities
- `Entity`, `EntityType` (`semantics/entity.py`) — physical entity declaration and its classification

`uses_addressed_sending: bool` (default `True`) distinguishes destination-addressed devices (VLD / D2 family, use BaseID+0 + destination field) from sender-addressed devices (4BS actuators, learn the gateway's sender at teach-in time and filter by it). The gateway uses this flag at teach-in time to decide whether to allocate a dedicated sender slot from the pool.

### 3. Semantics Layer

**Files:** `semantics/`

The semantics layer is the behavioural abstraction between raw EEP bytes and typed Python objects. It contains both the receive side (observers, observables, observations) and the send side (instructables, instructions).

Key semantic types:
- `entity.py` — `Entity` (physical entity declaration) and `EntityType` (sensor / actuator / combined classification)
- `observer_factory.py` — `ObserverFactory` (wraps an observer constructor for `EEPSpecification.observers`)
- `types.py` — `SemanticResolver` and `InstructionEncoder` type aliases
- `device_spec.py` — `DeviceSpec` (setup-time snapshot of a device's EEP and entities)

#### Observers

Each `Observer` subclass interprets a decoded `EEPMessage` for one specific entity and emits `Observation` objects.

- **`ScalarObserver`** (`observers/scalar.py`): Generic, parameterised by `observable` and `entity_id`. Reads `message.entities[observable]` and emits an `Observation`. Covers all plain scalar observables (temperature, illumination, motion, voltage, window state, …).
- **`CoverObserver`** (`observers/cover.py`): Stateful: takes the received position and angle values, infers `cover_state` from successive position deltas, and schedules a `loop.call_later()` timer handle to emit `stopped` after 1.5 s of radio silence. `stop()` cancels the timer. Emits one `Observation` with `entity_id="cover"` and `values={POSITION: …, ANGLE: …, COVER_STATE: …}`.
- **`ButtonObserver` / `F6_02_01_02_ButtonObserver`** (`observers/button.py`): Stateful: decodes rocker switch bit patterns into button events using `loop.call_later()` hold and release-timeout timer handles. `stop()` cancels all pending handles. Each button emits an `Observation` with its own `entity_id` (`"a0"`, `"b0"`, …). Event semantics: `pressed` fires immediately on press; `clicked` fires on release if the press was short; `held` fires when the hold threshold elapses while still pressed; `released` fires only after a hold — it is not emitted for short presses. This makes the event pairs semantically distinct: `pressed`/`clicked` bracket a tap, (`pressed`/)`held`/`released` bracket a hold.
- **`MetaDataObserver`** (`observers/metadata.py`): Emits RSSI, last-seen timestamp, and telegram count as separate `Observation` objects. Always prepended to a device's observer list by the gateway.

#### Instructions

Typed `Instruction` subclasses live in `semantics/instructions/`. Each subclass declares a `ClassVar[Instructable]` named `action` and typed fields for its parameters.

### 4. Device Type Catalog

**File:** `eep/device_type.py`

`DeviceType` maps a manufacturer and model name to an EEP. It is the public-facing unit for device selection in UI integrations (e.g. Home Assistant) — users pick a device by name rather than entering an EEP code directly.

```python
@dataclass(frozen=True)
class DeviceType:
    manufacturer: Manufacturer | None  # None = generic (any manufacturer)
    model: str
    eep: EEP
    description: str = ""

    @property
    def id(self) -> str: ...  # stable NAMESPACE/CODE string
```

**`DEVICE_TYPES: dict[str, DeviceType]`** is the full catalog keyed by `DeviceType.id` for O(1) lookup (e.g. `DEVICE_TYPES["NODON/SIN-2-RS-01"]`). It contains generic entries (auto-derived from `EEP_SPECIFICATIONS`, `manufacturer=None`) and manufacturer-specific entries (known physical products). The two are always in sync — every supported EEP has exactly one generic entry.

**`device_type_for_eep(eep: EEP) -> DeviceType`** is the free-function factory for obtaining the generic DeviceType for a given EEP. It raises `KeyError` if the EEP is not in the catalog. Both are exported from the top-level `enocean_async` package.

**IDs** use a `{NAMESPACE}/{CODE}` format in uppercase:
- `EEP/A5-02-01` — generic entry for a plain EEP
- `ELTAKO/A5-06-01` — generic entry for an Eltako-qualified EEP variant
- `ELTAKO/FAH65S` — manufacturer-specific product entry

At teach-in time the gateway uses `device_type_for_eep` to associate the taught-in EEP with a generic `DeviceType`; integrations can then offer the user the full list of specific products with the same EEP as alternatives.

### 5. Device Layer

**File:** `device.py`

`Device` is a runtime object (created by `add_device()`) holding the device's address, `DeviceType` (EEP + optional manufacturer/model), name, and instantiated `Observer` list. Every incoming `EEPMessage` is forwarded to all observers. `Device.eep` is a convenience property returning `device_type.eep`.

### 6. Gateway Layer

**File:** `gateway.py`

The top-level orchestrator. For receiving: serial I/O → packet routing → ERP1 routing → EEP decoding → observer dispatch. For sending: `send_command()` → encoder lookup → `EEPHandler.encode()` → `send_esp3_packet()`.

Layered callbacks for application code:
- `add_esp3_received_callback` — raw packet level
- `add_erp1_received_callback` — parsed telegram (filterable by sender)
- `add_eep_message_received_callback` — decoded EEP message (filterable by sender)
- `add_observation_callback` — semantic entity state updates from observers
- `add_new_device_callback` — first telegram seen from an unknown EURID
- `add_device_taught_in_callback` — fires after a device is successfully taught in and auto-registered, carrying `(address: EURID, eep: EEP)`

`gateway.device_spec(address)` returns a `DeviceSpec` for one registered device. `gateway.device_specs` (property) returns `dict[EURID, DeviceSpec]` for all registered devices.

#### Teach-in

The gateway handles UTE and 4BS teach-in telegrams during an active learning session (`start_learning()`). On a successful teach-in it calls `add_device()` internally and emits `DeviceTaughtInCallback`. For sender-addressed devices it allocates the lowest free slot from the BaseID+1…+127 pool.

Both UTE and 4BS-with-profile support bidirectional teach-in: the gateway sends a protocol-level response acknowledging or rejecting the pairing. For UTE this is mandatory; for 4BS it is conditional on the device requesting a response (`learn_status=QUERY`). Re-teach-in of an already-registered device is handled gracefully — same EEP is acknowledged and ignored; a different EEP updates the registration.

**Focused learning mode:** `start_learning(focus_device: EURID | None = None)` — when `focus_device` is set, UTE and 4BS handlers silently discard telegrams from any other EURID. This allows integrations to retrigger teach-in for a specific device (e.g. from the device's config page) without risk of accidentally registering an unrelated device that happens to be in teaching mode nearby. `stop_learning()` always clears the focus.

The gateway can also initiate outbound teach-in for Eltako-style sender-addressed devices (those with `EEPSpecification.teach_in_payload` set): `send_command(address, TeachIn())` sends the fixed 4BS payload that registers the gateway's sender slot with the device.

See [TEACHIN.md](https://github.com/henningkerstan/enocean-async/blob/main/docs/TEACHIN.md) for the full behavior.

#### Gateway learning entities and sender_slot

The gateway itself exposes additional observable and configurable entities beyond the connection-status group. All are available via `gateway.gateway_entities`:

- **`learning_active`** — `Observable.LEARNING_ACTIVE` (bool); emitted `True`/`False` on session start/stop
- **`learning_remaining`** — `Observable.LEARNING_REMAINING` (seconds); counted down once per second via `loop.call_later()` while learning is active
- **`learning_toggle`** — trigger entity accepting `Instructable.TOGGLE_LEARNING`; `gateway_command(ToggleLearning())` starts or stops the session; `ToggleLearning(for_device=eurid)` starts a focused session
- **`learning_timeout`** — `CONFIG_NUMBER`; default session length in seconds
- **`learning_sender`** — `CONFIG_ENUM`; sender slot used when the gateway responds during teach-in

Every registered device also receives a **`sender_slot`** `CONFIG_ENUM` entity (injected by `device_spec()`). Updating it via `set_device_config(address, "sender_slot", value)` resolves the string to a `BaseAddress` or `EURID`, validates no slot collision, and updates `device.sender` in place. The next `send_command()` or `TeachIn()` picks up the new sender automatically.

#### Auto-reconnect

When the serial connection is lost unexpectedly, the gateway automatically attempts to re-establish it. This is controlled by the `auto_reconnect` parameter. When enabled (default) and the connection is lost, the gateway tries to reconnect for 1 hour. A successful reconnect cancels the task and logs a confirmation. Exhausting all attempts logs a final error and stops retrying.

---

## Key design decisions

### EEP definitions are self-describing

`EEPSpecification.entities` (physical entity model), `observers` (receive behaviour), and `encoders` (send encoding) mean the gateway contains zero EEP-specific logic. Adding a new EEP or a new commandable instructable never requires touching `gateway.py`.

### Entities are physical things, declared in the EEP

Each EEP statically declares its `Entity` list. Entities are physical real-world sub-units (push buttons, relay channels, cover motors, sensor elements). The EEP fully specifies what entities exist — including their observable types and accepted instructables — before any telegram arrives.

### Observable carries intrinsic metadata

`Observable` is a `str, Enum` whose members carry `unit`, `kind`, and `possible_values` as intrinsic properties. The unit is fixed per observable type — temperature is always in `°C`, illumination always in `lx`. If two quantities differ in unit, they are distinct `Observable` members. `possible_values` for ENUM-kinded observables lives on `Observable` rather than on `Entity`, so any consumer can read allowed values without a device context. This eliminates all scattered `(Observable, str | None)` unit pairs and per-entity `possible_values` dicts that previously appeared in factory declarations, `DeviceSpec`, and `Entity`.

### Observation is entity-centric, not observable-centric

A single telegram updates an entity's state. When a cover reports its position, angle, and state simultaneously, a single `Observation` with `values={POSITION: 75, ANGLE: 0, COVER_STATE: "open"}` is emitted — not three separate events. The consumer receives one coherent update per entity per telegram. Partial updates (when a telegram only carries some of an entity's observables) are naturally expressed as a `values` dict with fewer keys.

### Two-vocabulary `EEPMessage`

`EEPMessage.raw` holds the raw integer field view (spec field IDs: `"TMP"`, `"ILL1"`). `EEPMessage.decoded` holds per-field `ValueWithContext` objects (scaled value + unit + name) by the same field IDs. `EEPMessage.values` holds the semantic observable view keyed by `Observable` enum members, also as `ValueWithContext`. Observers always read from `values`, making them EEP-agnostic: `ScalarObserver(observable=TEMPERATURE)` works for A5-02, A5-04, A5-08, or any future temperature-bearing EEP without modification.

### Semantic resolvers bridge multi-field observables

Some EEP profiles spread one observable across multiple fields (A5-06: two illumination ranges + a select bit). `SemanticResolver` callables live in the EEP definition module and run as pass 4 of the decoder. Observers remain oblivious to this complexity.

---

## Adding a new EEP

1. Create a module under `eep/<rorg>/` with an `EEPSpecification` or `SimpleProfileSpecification` instance.
2. Declare `entities` — one `Entity` per physical entity, with its `observables` and `actions`.
3. Annotate fields with `observable` where a 1:1 mapping to an observable exists. Add a `SemanticResolver` for multi-field combinations.
4. Populate `observers` with the appropriate factory callables (e.g. `scalar_factory`, `cover_factory`, `f6_button_factory`).
5. Set `uses_addressed_sending=False` if the device is sender-addressed (learns the gateway's BaseID+n at teach-in). Default is `True` (VLD / destination-addressed).
5a. For sender-addressed devices where the gateway announces itself with a fixed 4BS payload (e.g. Eltako actuators), set `teach_in_payload: bytes` (4 bytes). The gateway's `send_command(address, TeachIn())` will send this payload directly, bypassing `EEPHandler.encode()`. These devices get a `teach_in` trigger entity in `DeviceSpec.entities` but **not** `learning_toggle`/`learning_remaining` in `gateway_entities`.
6. Optionally populate `encoders` if the device accepts instructions. Add the corresponding `Instruction` subclass in `semantics/instructions/<profile>.py`.
7. Register in `eep/__init__.py`'s `EEP_SPECIFICATIONS`. A generic `DeviceType` entry is auto-derived from this automatically.
8. Optionally add known physical products for this EEP to `_MANUFACTURER_TYPES` in `eep/device_type.py`.

No changes to `gateway.py`, `device.py`, or any observer class are required.
