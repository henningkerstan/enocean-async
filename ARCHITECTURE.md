# Architecture

<!-- This file documents the architecture of the enocean-async library. -->

## Overview

`enocean-async` is an asyncio-based Python library for communicating with EnOcean devices over an EnOcean USB gateway. The library has two symmetric pipelines:

- **Observable pipeline** (receive): raw radio telegrams → typed `StateChange` objects carrying values like `temperature=21.3 °C` or `position=75`.
- **Action pipeline** (send): high-level commands → encoded `ERP1Telegram` → radio signal.

Each pipeline layers protocol detail away from the application. The gateway orchestrates both.

---

## Observables and Actions

These two concepts form the semantic vocabulary of the library.

### Observables

An **observable** is any quantity a device exposes that can be watched over time — whether the device is a pure sensor (temperature, illumination) or an actuator reporting its own state (cover position, window handle state). The gateway side always _observes_: it receives a telegram, decodes it, and emits an updated value. The physical nature of the device (sensor vs. actuator) is irrelevant to this abstraction.

Observables are identified by `ObservableUID` string constants (`capabilities/observable_uids.py`):

```python
class ObservableUID:
    TEMPERATURE   = "temperature"
    ILLUMINATION  = "illumination"
    POSITION      = "position"
    COVER_STATE   = "cover_state"
    WINDOW_STATE  = "window_state"
    ...
```

An observable update is delivered as a `StateChange`:

```python
@dataclass
class StateChange:
    device_address: SenderAddress   # which device
    observable_uid: str             # which observable (ObservableUID constant)
    value: Any                      # the new value
    unit: str | None                # physical unit, if applicable
    timestamp: float                # wall-clock time
    source: StateChangeSource       # TELEGRAM or TIMER
```

### Actions

An **action** is a command sent _to_ a device — telling a cover to move, a dimmer to change brightness, a fan to change speed. Actions are identified by `ActionUID` string constants (`capabilities/action_uid.py`):

```python
class ActionUID:
    SET_COVER_POSITION = "set_cover_position"    # D2-05-00: position + angle
    STOP_COVER         = "stop_cover"            # D2-05-00
    DIM                = "dim"                   # A5-38-08
    SET_FAN_SPEED      = "set_fan_speed"         # D2-20-02
```

A command is represented as a `DeviceCommand`:

```python
@dataclass
class DeviceCommand:
    action: str                  # ActionUID constant
    values: dict[str, int]       # EEP field_id → raw integer value
```

The gateway exposes the send pipeline via a single method:

```python
await gateway.send_command(
    destination=device_address,     # EURID | BaseAddress
    action=ActionUID.STOP_COVER,
    values={"CHN": 15},             # field_id → raw value
    sender=None,                    # optional; defaults to device.sender or base_id
)
```

### Relationship between actions and observables

Some actions have a direct observable counterpart — setting cover position (`SET_COVER_POSITION`) will eventually result in `POSITION` and `COVER_STATE` observable updates coming back from the device. Others are fire-and-forget with no reply (e.g., `DIM` on A5-38-08).

The library **does not enforce** a formal link between an action and the observables it affects — this mapping is device-dependent, bidirectionality is EEP-specific, and enforcing it would add significant complexity for little benefit at the library level. The connection is documented per-EEP by convention: an EEP that defines `command_encoders` should also document which observables its actions affect. Application code (e.g., a Home Assistant integration) is the right place to model the full bidirectional entity (cover = position observable + set_output/stop actions).

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
  .values    {field_id  → EEPMessageValue}   ← EEP spec vocabulary: "TMP", "ILL1", "R1"
  .entities  {observable_uid → EntityValue}        ← semantic vocabulary: "temperature", "illumination"
    │ Capability.decode()  (one call per capability in device.capabilities)
    ├── ScalarCapability(observable_uid=TEMPERATURE) → reads entities["temperature"]
    ├── ScalarCapability(observable_uid=ILLUMINATION) → reads entities["illumination"]
    ├── CoverCapability → reads entities["position"]+entities["angle"], infers "cover_state"
    ├── PushButtonCapability → reads values["R1"], values["EB"], … (no observable_uid mapping)
    └── MetaDataCapability → reads rssi, generates timestamps
    │ _emit()
    ▼
StateChange(device_address, observable_uid, value, unit, timestamp, source)
    │ on_state_change callback
    ▼
Application
```

The `EEPHandler` runs four passes during decode:

| Pass | Purpose |
|------|---------|
| **1 — Raw extraction** | Read every field's raw int from the telegram bitstring into a scratch dict. Done first so interdependent scale functions have full context. |
| **2 — Value decoding** | Apply enum lookup or linear scaling per field → `EEPMessage.values[field.id]` as `EEPMessageValue(raw, value, unit)`. |
| **3 — Observable propagation** | For each field with `observable_uid` set: copy `values[field.id]` → `entities[observable_uid]` as `EntityValue(value, unit)`. Translates spec vocabulary to semantic vocabulary. |
| **4 — Semantic resolvers** | Run `SemanticResolver` callables that synthesise a single observable from multiple fields (e.g., A5-06: pick ILL1 or ILL2 based on range-select bit). |

Note: `EEPMessage.values` contains `EEPMessageValue` (raw int + decoded value + unit), while `EEPMessage.entities` contains the lighter `EntityValue` (decoded value + unit only — raw is not needed at the semantic layer).

---

## Send pipeline (Actions)

```
Application
    │ gateway.send_command(destination, ActionUID.STOP_COVER, values={...})
    ▼
DeviceCommand(action, values: {field_id → raw_int})
    │ EEPSpecification.command_encoders[action](command)
    ▼
EEPMessage
  .message_type  ← selects which telegram type to encode
  .values        ← {field_id → EEPMessageValue(raw)} filled in by the encoder
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

The encoder in each EEP definition is a simple function that maps a `DeviceCommand` to an `EEPMessage` with `message_type.id` set and `values` filled with raw field values. Raw values are used throughout — no reverse scaling is needed for current commandable EEPs, where scale range equals raw range or fields are enum-keyed. The gateway sets `message.sender` and `message.destination` before calling `EEPHandler.encode()`.

---

## Layers

### 1. Serial / ESP3 Layer / ERP1 Layer

**Files:** `esp3/`, `erp1/`

`EnOceanSerialProtocol3` (an `asyncio.Protocol`) reassembles byte streams into `ESP3Packet` objects. The gateway routes packets by type: `RADIO_ERP1` → ERP1 processing; `RESPONSE` → matched to a pending `send_esp3_packet()` future.

`ERP1Telegram` provides bit-addressable access to the payload (`bitstring_raw_value`, `set_bitstring_raw_value`) used by both the decode and encode paths.

### 2. EEP Layer

**Files:** `eep/profile.py`, `eep/handler.py`, `eep/message.py`, `eep/a5/`, `eep/f6/`, `eep/d2/`

Every supported EEP is a module-level `EEPSpecification` (or `SimpleProfileSpecification`) instance in `EEP_SPECIFICATIONS`, keyed by `EEP` (the ID struct).

The two key types are:

- **`EEP`** (`eep/id.py`): The 4-tuple identifier — `rorg`, `func`, `type_`, optional `manufacturer`. Used as the dict key in `EEP_SPECIFICATIONS` and as a reference in `EEPMessage.eep`.
- **`EEPSpecification`** (`eep/profile.py`): The full profile — `cmd_size`, `cmd_offset`, `telegrams` dict, `semantic_resolvers`, `capability_factories`. The simpler `SimpleProfileSpecification` is a convenience subclass for single-telegram EEPs (no CMD field; wraps datafields into a single `EEPTelegram` at key `0`).

`EEPDataField` is the atomic unit: bit offset, size, scale functions, unit function, enum map, and optional `observable_uid` annotation that bridges the spec and semantic vocabularies.

`EEPSpecification` carries four extension points: `telegrams`, `semantic_resolvers`, `capability_factories` (for the receive path), and `command_encoders` (for the send path).

The last field in each `EEPTelegram.datafields` must cover the last meaningful bit of the telegram. This allows `EEPHandler.encode()` to compute the buffer size automatically as `ceil((max(f.offset + f.size for f in datafields) [+ cmd_size if CMD at end]) / 8)`.

### 3. Capability Layer

**Files:** `capabilities/`

Capabilities are the behavioural layer. Each subclass interprets a decoded `EEPMessage` for one specific observable and emits `StateChange` objects.

- **`ScalarCapability`** (`scalar.py`): Generic, parameterised by `observable_uid`. Reads `message.entities[observable_uid]` and emits a `StateChange`. Covers all plain scalar observables (temperature, illumination, motion, voltage, window state, …).
- **`CoverCapability`** (`position_angle.py`): Stateful: it takes the received position and angle values, infers `cover_state` from successive position deltas, and runs an asyncio watchdog to emit `stopped` after 1.5 s of radio silence.
- **`PushButtonCapability` / `F6_02_01_02PushButtonCapability`** (`push_button.py`): Stateful: decodes rocker switch bit patterns into button events (pushed, hold, click, double click, released) using timeouts.
- **`MetaDataCapability`** (`metadata.py`): Emits RSSI, last-seen timestamp, and telegram count. Always prepended to a device's capability list by the gateway.

### 4. Device Layer

**Files:** `device/device.py`, `device/catalog.py`

`Device` is a runtime object (created by `add_device()`) holding the device's address, EEP ID, name, and instantiated `Capability` list. Every incoming `EEPMessage` is forwarded to all capabilities.


### 5. Gateway Layer

**File:** `gateway.py`

The top-level orchestrator. For receiving: serial I/O → packet routing → ERP1 routing → EEP decoding → capability dispatch. For sending: `send_command()` → encoder → `EEPHandler.encode()` → `send_esp3_packet()`.

Layered callbacks for application code:
- `add_esp3_received_callback` — raw packet level
- `add_erp1_received_callback` — parsed telegram (filterable by sender)
- `add_eep_message_received_callback` — decoded EEP message (filterable by sender)
- `add_state_change_callback` — semantic observable updates from capabilities

#### Auto-reconnect

When the serial connection is lost unexpectedly, the gateway automatically attempts to re-establish it. This is controlled by the `auto_reconnect` parameter. When enabled (default) and the connection is lost, the gateway tries to reconnect for 1 hour. A successful reconnect cancels the task and logs a confirmation. Exhausting all attempts logs a final error and stops retrying.

---

## Key design decisions

### EEP definitions are self-describing

`EEPSpecification.capability_factories` (receive) and `EEPSpecification.command_encoders` (send) mean the gateway contains zero EEP-specific logic. Adding a new EEP or a new commandable action never requires touching `gateway.py`.

### Two-vocabulary `EEPMessage`

`EEPMessage.values` holds the raw EEP field view (spec field IDs: `"TMP"`, `"ILL1"`), each as an `EEPMessageValue(raw, value, unit)`. `EEPMessage.entities` holds the semantic observable view (`ObservableUID` strings: `"temperature"`, `"illumination"`), each as a lighter `EntityValue(value, unit)` — the raw int is not needed at the semantic layer. Capabilities always read from `entities`, making them EEP-agnostic: `ScalarCapability(observable_uid="temperature")` works for A5-02, A5-04, A5-08, or any future temperature-bearing EEP without modification.

### Semantic resolvers bridge multi-field observables

Some EEP profiles spread one observable across multiple fields (A5-06: two illumination ranges + a select bit). `SemanticResolver` callables live in the EEP definition module and run as pass 4 of the decoder. Capabilities remain oblivious to this complexity.

### Observable and Action UIDs are decoupled

`ObservableUID` names things you _receive_. `ActionUID` names things you _send_. They are intentionally separate: "stop cover" is an action but has no observable counterpart; "set position" is an action that affects the `POSITION` and `COVER_STATE` observables. Conflating the two vocabularies would force artificial mappings for commands that have no observable counterpart and vice versa.


---

## Adding a new EEP

1. Create a module under `eep/<rorg>/` with an `EEPSpecification` or `SimpleProfileSpecification` instance.
2. Annotate fields with `observable_uid` where a 1:1 mapping to an observable exists. Add a `SemanticResolver` for multi-field combinations.
3. Populate `capability_factories` with `ScalarCapability` lambdas (for plain scalars) or specialised capability constructors (for stateful logic).
4. Optionally populate `command_encoders` if the device accepts commands.
5. Register in `eep/__init__.py`'s `EEP_SPECIFICATIONS`.

No changes to `gateway.py`, `device/device.py`, or any capability class are required.
