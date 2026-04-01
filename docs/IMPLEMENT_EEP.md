# Implementing a new EEP

A step-by-step guide for adding support for a new EnOcean Equipment Profile (EEP).

---

## 1. Read the spec

Download the relevant EEP from the [EnOcean Alliance EEPViewer](https://tools.enocean-alliance.org/EEPViewer). Key things to capture:

- **RORG** (e.g. `D2` = VLD, `A5` = 4BS, `F6` = RPS)
- **FUNC / TYPE** — the profile family and all its type variants
- **Payload layout** — bit offsets and sizes for every field, per CMD
- **CMD field** — location (offset, size) and enumerated command IDs
- **ECID field** — if present, its location and sub-command IDs
- **Field semantics** — enum entries, scaling formulas, physical units
- **Which fields are observable** (reported state) vs. command-only (sent to device)
- **Shared telegram format across type variants** — many families (like D2-01) share one wire format across all TYPEs; only the supported command subset differs per device

---

## 2. Choose the right profile class

| Situation | Class |
|-----------|-------|
| Single telegram, no CMD field | `SimpleProfileSpecification` |
| Multiple telegrams dispatched on a CMD field | `EEPSpecification` |

`SimpleProfileSpecification` wraps a flat field list into a single telegram at key `0` automatically. For anything with a CMD field, use `EEPSpecification` and supply a `telegrams: dict[int, EEPTelegram]`.

---

## 3. Create the module

Place the file at `enocean_async/eep/<rorg>/<rorg>_<func>_<type>.py` (or `<rorg>_<func>.py` for a whole family).

If this is the first EEP in an RORG directory, add an `__init__.py` alongside it.

### 3a. Single-telegram EEP (SimpleProfileSpecification)

```python
from enocean_async.eep.profile import EEPDataField, Entity, SimpleProfileSpecification
from enocean_async.eep.id import EEP
from enocean_async.semantics.observable import Observable
from enocean_async.semantics.observers.scalar import scalar_factory

_ENTITIES = [Entity(id="temperature", observables=frozenset({Observable.TEMPERATURE}))]

EEP_XX_YY_ZZ = SimpleProfileSpecification(
    eep=EEP("XX-YY-ZZ"),
    name="Human-readable profile name",
    datafields=[
        EEPDataField(
            id="FIELD_ID",
            name="Field name",
            offset=0,
            size=8,
            range_enum={0: "Off", 1: "On"},
            observable=Observable.SOME_OBSERVABLE,
        ),
        ...
    ],
    observers=[scalar_factory(Observable.SOME_OBSERVABLE)],
    entities=_ENTITIES,
)
```

### 3b. Multi-telegram EEP (EEPSpecification)

```python
from enocean_async.eep.profile import EEPDataField, EEPSpecification, EEPTelegram
from enocean_async.eep.id import EEP

EEP_XX_YY_ZZ = EEPSpecification(
    eep=EEP("XX-YY-ZZ"),
    name="Human-readable profile name",
    cmd_offset=<bit offset of CMD field>,
    cmd_size=<bit size of CMD field>,
    telegrams={
        0x1: EEPTelegram("Telegram name", [<fields>]),
        0x2: EEPTelegram("Telegram name", [<fields>]),
    },
    observers=[...],          # optional
    encoders={...},           # optional
)
```

---

## 4. Define `EEPDataField` correctly

```python
EEPDataField(
    id="FIELD_ID",         # short EEP spec identifier — used as dict key in raw_values
    name="Human name",
    offset=<bit offset>,   # from bit 0 of the EEP payload (not byte 0 of the radio packet)
    size=<bit size>,
    range_enum={0: "Off", 1: "On", ...},   # for enum fields
    # — OR — for numeric fields with linear scaling:
    range_min=0, range_max=255,
    scale_min_fn=lambda _: 0.0,
    scale_max_fn=lambda _: 100.0,
    unit_fn=lambda _: "°C",
    observable=Observable.TEMPERATURE,    # connect to semantic vocabulary
)
```

The `scale_min_fn`, `scale_max_fn`, and `unit_fn` arguments are callables of type
`Callable[[dict[str, int]], float | None]` and `Callable[[dict[str, int]], str]` respectively.
They receive the current telegram's raw field values and return the appropriate value, enabling
dynamic scaling (e.g. when a range selector field changes the interpretation of another field).
For constant scaling the lambdas simply ignore the argument: `lambda _: 40.0`.

**Enum dictionaries** can be built compactly with dict comprehensions:

```python
range_enum={
    0x00: "Off",
    **{i: f"{i}%" for i in range(1, 101)},
    **{i: "Reserved" for i in range(101, 128)},
}
```

**Last field** in each `EEPTelegram.datafields` must extend to the last meaningful bit; `EEPHandler.encode()` uses `max(f.offset + f.size)` to size the output buffer.

---

## 5. Handle shared structure across type variants

When many TYPE variants share the same wire format (e.g. D2-01 types 0x00–0x16):

1. Build a single `_TELEGRAMS: dict[int, EEPTelegram]` shared across all specs.
2. Use a factory function to stamp out the individual `EEPSpecification` objects:

```python
def _spec(type_id: int, name: str) -> EEPSpecification:
    return EEPSpecification(
        eep=EEP(f"XX-YY-{type_id:02X}"),
        name=f"Profile family – {name}",
        cmd_offset=4, cmd_size=4,
        telegrams=_TELEGRAMS,
        encoders=_ENCODERS,
    )

EEP_XX_YY_00 = _spec(0x00, "Type 0x00 – ...")
EEP_XX_YY_01 = _spec(0x01, "Type 0x01 – ...")
```

### Use a command registry for CMD-heavy families

If the EEP has many CMDs, define a registry as the single source of truth for IDs and names, then derive `range_enum` from it:

```python
@dataclass(frozen=True)
class _TelegramName:
    key: int
    name: str

_COMMANDS: dict[int, _TelegramName] = {
    0x1: _TelegramName(0x1, "Set output"),
    0x2: _TelegramName(0x2, "Set local"),
    ...
}

def _cmd(cmd_id: int) -> EEPDataField:
    c = _COMMANDS[cmd_id]
    return EEPDataField(id="CMD", name="Command", offset=4, size=4,
                        range_enum={c.key: c.name})
```

This ensures the CMD field's `range_enum` and the telegram's name are always in sync, and avoids repeating magic numbers.

### Use shared field constants and helpers for repeated structure

Fields that appear verbatim in multiple telegrams should be named constants or factory functions:

```python
# Named constant
_IO_FIELD = EEPDataField(id="IO", name="I/O channel", offset=11, size=5,
                         range_enum={...})

# Factory function — use when the field varies by one parameter
def _io(offset: int = 11, *, not_applicable_at_1e: bool = False) -> EEPDataField:
    return EEPDataField(...)
```

---

## 6. Extended commands (CMD + ECID)

Some EEPs use a two-level dispatch: an outer CMD field and an inner ECID field. The current `EEPHandler` dispatches only on CMD; ECID sub-dispatch is not yet implemented.

Workaround: register ECID sub-telegrams under synthetic keys (e.g. `0xF0`, `0xF1`) in the telegrams dict with a note that ECID dispatch is pending:

```python
_TELEGRAMS = {
    ...
    0xF0: ...,   # CMD=0xF / ECID=0x00  (pending ECID dispatch)
    0xF1: ...,   # CMD=0xF / ECID=0x01
}
```

---

## 7. Observables

`Observable` (`semantics/observable.py`) is the semantic vocabulary that ties EEP field data to observers. It is a `StrEnum`; each member carries its `unit`, `kind` (`SCALAR`/`BINARY`/`ENUM`), and optionally `possible_values`.

- **Reuse an existing constant** if the concept is the same (e.g. `Observable.TEMPERATURE`, `Observable.POSITION`).
- **Add a new constant** only if no existing constant fits. Add it to `Observable` with the appropriate `(name, unit, kind)` tuple and group it with related constants.

Annotate fields with `observable=Observable.XXX` where there is a clear 1:1 mapping from one EEP field to one observable. For a multi-field observable (e.g. combining a raw value with a range-select bit), use a `SemanticResolver` in `semantic_resolvers` instead.

---

## 8. Semantic resolvers

Use `semantic_resolvers` when an `Observable` value cannot be derived from a single field in isolation — for example when a range selector field governs the interpretation of a sensor field, or when post-processing (inverse scaling, unit conversion) is needed after decoding.

A resolver is a callable with signature:

```python
def my_resolver(
    raw: dict[str, int],
    scaled: dict[str, ValueWithContext],
    config: dict,
) -> ValueWithContext | None:
    ...
```

Register it in the spec:

```python
EEPSpecification(
    ...
    semantic_resolvers={Observable.TEMPERATURE: my_resolver},
)
```

`config` contains the device's per-device config (see §10). Return `None` to suppress the observable for this telegram.

---

## 9. Instructions (send path)

If the EEP accepts commands:

1. Add a constant to `Instructable` (`semantics/instructable.py`) with a comment naming the EEP family.
2. Create a typed `Instruction` subclass in `semantics/instructions/<family>.py`:

```python
from dataclasses import dataclass
from ..instructable import Instructable
from ..instruction import Instruction

@dataclass
class SetOutput(Instruction):
    entity_id: str = "output"
    action: ClassVar[Instructable] = Instructable.SET_OUTPUT
    output_value: int = 0
    channel: int = 0x1E
```

3. Write an encoder function in the EEP module:

```python
from enocean_async.eep.message import EEPMessageType, RawEEPMessage

def _encode_set_output(action: SetOutput, _config: dict) -> RawEEPMessage:
    msg = RawEEPMessage(
        sender=None,
        message_type=EEPMessageType(id=0x01, description=_COMMANDS[0x1].name),
    )
    msg.raw["OV"] = action.output_value
    return msg
```

4. Register it in the spec's `encoders`:

```python
encoders={Instructable.SET_OUTPUT: _encode_set_output}
```

Encoder signature is `(instruction: Instruction, config: dict) -> RawEEPMessage`. The `config` dict contains the device's per-device config (see §10). Use `lambda a, _: _encode_foo(a)` when the encoder doesn't need config.

---

## 10. Observers

Observers consume decoded `EEPMessage` data and emit `Observation` objects. They are instantiated per-device at registration time via `ObserverFactory`. Supply them in the spec's `observers` list.

Available built-in factories (from `semantics/observers/`):

- **`scalar_factory(observable, entity_id=...)`** — covers all plain scalar observables (temperature, illumination, output value, …).
- **`cover_factory(message_type_id=4)`** — stateful; infers cover state from successive position deltas.
- **`f6_button_factory()`** — stateful; decodes rocker-switch bit patterns (F6-02-01/02).

For a new EEP carrying only scalar observables:

```python
from enocean_async.semantics.observers.scalar import scalar_factory

observers=[
    scalar_factory(Observable.TEMPERATURE),
    scalar_factory(Observable.HUMIDITY),
]
```

`MetaDataObserver` (RSSI, last_seen, telegram_count) is always prepended automatically by the gateway — do not add it yourself.

---

## 11. Config entities (per-device configuration)

If the EEP has runtime-configurable parameters (brightness limits, ramp time, operating mode, etc.), declare them as `Entity` objects with a `config_spec` in the `entities` list. The gateway auto-populates `Device.config` from defaults at `add_device()` time.

### Config spec types

| Type | `EntityCategory` | Python type in `Device.config` |
|---|---|---|
| `EnumOptions(options=("a","b"), default="a")` | `CONFIG` | `str` |
| `BoolOption(default=False)` | `CONFIG` | `str` (`"no"` / `"yes"`) |
| `NumberRange(min_value=0, max_value=100, step=1, unit="%", default=0.0)` | `CONFIG` | `float` |

`BoolOption(default=False)` is a convenience factory: it returns `EnumOptions(options=("no","yes"), default="no")`.

### Example

```python
from enocean_async.semantics.entity import BoolOption, Entity, EntityCategory, EnumOptions, NumberRange

_MIN_BRIGHTNESS = Entity(
    id="min_brightness",
    config_spec=NumberRange(min_value=0.0, max_value=100.0, step=1.0, unit="%", default=0.0),
    category=EntityCategory.CONFIG,
)

_STORE = Entity(
    id="store",
    config_spec=BoolOption(),        # EnumOptions(options=("no", "yes"), default="no")
    category=EntityCategory.CONFIG,
)
```

Add these to `EEPSpecification(entities=[..., _MIN_BRIGHTNESS, _STORE])`. Entities with no `default` in their `config_spec` are not written to `Device.config`.

---

## 12. Register the EEP

### In the RORG `__init__.py`

```python
# enocean_async/eep/<rorg>/__init__.py
from .<module> import EEP_XX_YY_ZZ

__all__ = ["EEP_XX_YY_ZZ"]
```

### In `eep/__init__.py`

```python
from .<rorg> import EEP_XX_YY_ZZ

EEP_SPECIFICATIONS: dict[EEP, EEPSpecification] = {
    ...
    EEP_XX_YY_ZZ.eep: EEP_XX_YY_ZZ,
}
```

For a family with many type variants, import and register each one.

---

## 13. Update SUPPORTED_DEVICES.md

Run `python scripts/generate_list_of_devices.py` to regenerate the supported devices table (this also happens automatically via the pre-commit hook).

---

## 14. Verify

```bash
pytest tests/ -q
```

New EEPs are automatically picked up by the parametrised profile smoke tests in `tests/test_eep_profile.py` as soon as they are registered in `EEP_SPECIFICATIONS`. No new test file is needed for the smoke tests; add targeted tests only for non-trivial field logic or encoder behaviour.

---

## Appendix: Eltako devices and teach-in telegrams

Some Eltako actuators (shutters, dimmers, relays, valves) require a manufacturer-specific teach-in: Before the device will respond to commands, the gateway must send a **learn (teach-in) telegram** to register its sender address with the device. 

### `uses_addressed_sending = False`

Set this on the spec when the device uses sender-addressed communication:

```python
EEP_XX_YY_ZZ = SimpleProfileSpecification(
    ...
    uses_addressed_sending=False,
)
```

The gateway then allocates a dedicated BaseID+n sender slot per device (see `add_device()`).

### `teach_in_payload`

The learn telegram is a fixed 4-byte 4BS payload (DB3..DB0). Add it to the spec:

```python
EEP_XX_YY_ZZ = SimpleProfileSpecification(
    ...
    uses_addressed_sending=False,
    teach_in_payload=bytes([0xFF, 0xF8, 0x0D, 0x80]),  # FSB family
)
```

Known Eltako actuator learn telegram payloads (from "Inhalte der Eltako-Funktelegramme"):

| Devices | DB3 | DB2 | DB1 | DB0 |
|---|---|---|---|---|
| FSB14, FSB61, FSB71, FJ62 (shutters) | `0xFF` | `0xF8` | `0x0D` | `0x80` |
| FUD14/61/71, FDG14/71L, FSR14/61/71 etc. (dimmers/relays) | `0xE0` | `0x40` | `0x0D` | `0x80` |
| FRGBW14, FRGBW71L, FWWKW71L (RGB/WW dimmers) | `0xFF` | `0xF8` | `0x0D` | `0x87` |
| FHK61, FHK61SSR (heating valve) | `0x40` | `0x30` | `0x0D` | `0x87` |
| FSUD-230V | `0x02` | `0x00` | `0x00` | `0x00` |

### `_TEACH_IN_ENTITY`

Add a teach-in trigger entity to any sender-addressed Eltako spec so integrations can expose the commissioning action:

```python
from ...semantics.entity import Entity, EntityCategory
from ...semantics.instructable import Instructable

_TEACH_IN_ENTITY = Entity(
    id="teach_in",
    actions=frozenset({Instructable.TEACH_IN}),
    category=EntityCategory.CONFIG,
)
```

Add it to `entities=[..., _TEACH_IN_ENTITY]`.

### Sending the learn telegram

The caller issues `TeachIn()` after `add_device()`:

```python
gateway.add_device(address, EEP("A5-7F-3F.ELTAKO.FSB"), name="Living room blind")
await gateway.send_command(address, TeachIn())
```

The gateway detects `Instructable.TEACH_IN`, bypasses the normal encoder, and sends `teach_in_payload` as a 4BS ERP1 telegram from the device's registered sender slot. No encoder registration is needed in the spec — `teach_in_payload` is the sole source of truth.

### Separate Eltako variant specs

`EEP_A5_38_08` is shared with non-Eltako devices, so Eltako dimmers/relays get their own variant `EEP_A5_38_08_ELTAKO` (`eep=EEP("A5-38-08.ELTAKO")`). Follow the same pattern when an existing generic spec would need teach-in support added: create a manufacturer-specific variant rather than modifying the shared spec.

---

## Appendix: Reading vendor documentation (Eltako)

Eltako datasheets and older EnOcean documentation sometimes use **ESP2 terminology** instead of the current ESP3 terms. The key difference is the `ORG` field (Organisation) in ESP2, which maps directly to `RORG` in ESP3:

| ORG (ESP2) | RORG (ESP3) | Telegram type |
|---|---|---|
| `0x05` | `0xF6` | RPS — rocker switch |
| `0x06` | `0xD5` | 1BS — 1-byte sensor |
| `0x07` | `0xA5` | 4BS — 4-byte sensor |
| `0x10` | `0xD2` | VLD — variable-length data |

So when an Eltako datasheet says **ORG = 0x07**, it means the EEP family is **A5-xx-xx** (4BS). Use the corresponding `RORG = 0xA5` when writing the EEP class.
