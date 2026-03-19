# enocean-async
A light-weight, asynchronous, fully typed Python library for communicating with EnOcean devices over a USB gateway. Based on [pyserial-asyncio-fast](https://pypi.org/project/pyserial-asyncio-fast/) and the [EnOcean Serial Protocol Version 3 (ESP3)](https://www.enocean.com/wp-content/uploads/Knowledge-Base/EnOceanSerialProtocol3-1.pdf).

> **Note:** The API may still change (even significantly!). Feedback and contributions are welcome.


## Features

### Receive pipeline — observables
Incoming radio telegrams are decoded into typed `Observation` objects. Callbacks are available at every stage for lower-level access:

```python
# Stage 4 — semantic: one Observation per entity per device
gateway.add_observation_callback(lambda obs: print(obs))
# Observation(device_id=…, entity_id='temperature', values={Observable.TEMPERATURE: 21.3}, …)

# Stage 3 — decoded EEP message (field values + semantic entities)
gateway.add_eep_message_received_callback(lambda msg: ..., sender_filter=eurid)

# Stage 2 — parsed ERP1 telegram (RORG, sender, raw payload bits)
gateway.add_erp1_received_callback(lambda erp1: ...)

# Stage 1 — raw ESP3 packet (before any parsing)
gateway.add_esp3_received_callback(lambda pkt: ...)
```

`Observable` members are stable string constants (`Observable.TEMPERATURE`, `Observable.ILLUMINATION`, `Observable.SWITCH_STATE`, `Observable.POSITION`, `Observable.COVER_STATE`, `Observable.ENERGY`, `Observable.POWER`, `Observable.GAS_VOLUME`, `Observable.GAS_FLOW`, `Observable.WATER_VOLUME`, `Observable.WATER_FLOW`, …). Each member carries its native unit as `Observable.TEMPERATURE.unit == "°C"`.

### Send pipeline — typed instructions
Instructions are sent to devices using typed `Instruction` subclasses:

```python
from enocean_async import SetCoverPosition, StopCover, SetSwitchOutput

await gateway.send_command(destination=device_eurid, command=SetCoverPosition(position=75))
await gateway.send_command(destination=device_eurid, command=StopCover())
await gateway.send_command(destination=device_eurid, command=SetSwitchOutput(state="on"))
```

### Device management
```python
from enocean_async import DeviceType, EEP, EURID

# Register by EEP — DeviceType.for_eep() looks up the generic catalog entry
gateway.add_device(address=EURID("01:23:45:67"),
                   device_type=DeviceType.for_eep(EEP("D2-05-00")),
                   name="Living room blind")

# Or register a known manufacturer-specific product from the catalog
from enocean_async import DEVICE_TYPES
nodon_shutter = next(dt for dt in DEVICE_TYPES if dt.identifier == "NODON/SIN-2-RS-01")
gateway.add_device(address=EURID("01:23:45:67"), device_type=nodon_shutter)
```

`DeviceType.for_eep(eep)` raises `ValueError` for unsupported EEPs. `DEVICE_TYPES` contains generic entries (one per supported EEP, `manufacturer=None`) and manufacturer-specific entries (known physical products). Each `DeviceType` has a stable `identifier` string in `NAMESPACE/CODE` format (e.g. `"EEP/D2-05-00"`, `"NODON/SIN-2-RS-01"`).

`EURID`, `BaseAddress`, and `Address` all accept an `int`, a colon-separated hex string (`"01:23:45:67"`), or a 4-byte sequence (`bytes`, `bytearray`, `list[int]`). Use `int(addr)` and `str(addr)` for numeric/string conversion.

### Learning / teach-in
```python
from enocean_async import TaughtInDevice

def on_taught_in(device: TaughtInDevice) -> None:
    print(f"New device: {device.address} ({device.eep})")

gateway.add_device_taught_in_callback(on_taught_in)
await gateway.start_learning(timeout=30)
# gateway now accepts teach-in telegrams and auto-registers devices
gateway.stop_learning()
```

Supported teach-in methods:
- **UTE**: automatic bidirectional response; sender address auto-allocated from the base ID pool
- **4BS with profile**: auto-registered when EEP is supported; bidirectional response always sent
1BS teach-in is intentionally not auto-registered (no EEP information available). The `NewDeviceCallback` fires in all cases.

See [TEACHIN.md](https://github.com/henningkerstan/enocean-async/blob/main/docs/TEACHIN.md) for the full teach-in and teach-out behavior.

### Gateway utilities
- Retrieve EURID, Base ID and firmware version info
- Change the Base ID
- Auto-reconnect: when the serial connection is lost, the gateway retries for up to 1 hour


## What works
- Full receive pipeline: raw serial bytes → ESP3 → ERP1 → EEP decode → observers → `Observation` callbacks
- Full send pipeline: typed `Instruction` → `EEPHandler.encode()` → ERP1 → ESP3 → serial
- Device registration with per-device EEP and observer instantiation
- Learning mode: UTE and 4BS-with-profile teach-in (auto-response, device registration, sender pool allocation); 4BS re-teach-in with EEP change supported
- `DeviceTaughtInCallback` with EURID + EEP on successful teach-in
- Auto-reconnect on connection loss
- EURID, Base ID, firmware version retrieval; Base ID change
- Parsing of all EEPs listed in [SUPPORTED_DEVICES.md](https://github.com/henningkerstan/enocean-async/blob/main/docs/SUPPORTED_DEVICES.md)
- Sending instructions for: D2-05-00 (covers), D2-20-02 (fan), A5-38-08 (dim gateway), D2-01 (switches/dimmers)


## What is missing / not yet implemented
- ECID sub-dispatch for D2-01 extended commands
- More EEPs (contributions welcome — see [SKILLS.md](https://github.com/henningkerstan/enocean-async/blob/main/docs/SKILLS.md) for the step-by-step guide)
- Logging coverage is partial


## Implemented EEPs
See [SUPPORTED_DEVICES.md](https://github.com/henningkerstan/enocean-async/blob/main/docs/SUPPORTED_DEVICES.md).


## Architecture

### Receive pipeline (observables)

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
  .values    {field_id → EEPMessageValue}   ← EEP spec vocabulary: "TMP", "ILL1", "R1"
  .entities  {observable → EntityValue}     ← semantic vocabulary: TEMPERATURE, ILLUMINATION
    │ Observer.decode()  (one call per observer in device.observers)
    ├── ScalarObserver(observable=TEMPERATURE)  → reads entities[TEMPERATURE]
    ├── ScalarObserver(observable=ILLUMINATION) → reads entities[ILLUMINATION]
    ├── CoverObserver    → reads entities[POSITION] + entities[ANGLE], infers COVER_STATE
    ├── ButtonObserver → reads values["R1"], values["EB"], … (stateful, hold timer)
    └── MetaDataObserver → emits rssi, last_seen, telegram_count
    │ _emit()
    ▼
Observation(device_id, entity_id, values, timestamp, source)
    │ add_observation_callback
    ▼
Application
```

### Send pipeline (instructions)

```
Application
    │ gateway.send_command(destination, command=SetCoverPosition(position=75))
    ▼
Instruction subclass  (typed dataclass with ClassVar[Instructable] action)
    │ spec.encoders[command.action](command)
    ▼
EEPMessage
  .message_type  ← selects which telegram type to encode
  .values        ← {field_id → EEPMessageValue(raw)} filled in by the encoder
    │ EEPHandler.encode()
    ├── Determine buffer size from field layout
    ├── Write CMD bits at cmd_offset / cmd_size
    └── Write each field's raw value at field.offset / field.size
    ▼
ERP1Telegram(rorg, telegram_data, sender, destination)
    │ .to_esp3()
    ▼
ESP3Packet
    │ Gateway.send_esp3_packet()
    ▼
Radio signal → Device
```

See [ARCHITECTURE.md](https://github.com/henningkerstan/enocean-async/blob/main/docs/ARCHITECTURE.md) for a detailed description of the EEP layer, the semantics layer, and the key design decisions.


## Contributing
See [CONTRIBUTING.md](https://github.com/henningkerstan/enocean-async/blob/main/CONTRIBUTING.md).


## Versioning
See [VERSIONING.md](https://github.com/henningkerstan/enocean-async/blob/main/VERSIONING.md) for the version scheme and bump instructions.


## Dependencies
This library has one dependency:
- [pyserial-asyncio-fast](https://pypi.org/project/pyserial-asyncio-fast/) (BSD-3 licensed)


## Technology documentation
- [EnOcean Serial Protocol Version 3 (ESP3)](https://www.enocean.com/wp-content/uploads/Knowledge-Base/EnOceanSerialProtocol3-1.pdf)
- [EnOcean Radio Protocol 1 (ERP1)](https://www.enocean.com/wp-content/uploads/Knowledge-Base/EnOceanRadioProtocol1.pdf)
- [EnOcean Alliance Specifications](https://www.enocean-alliance.org/specifications/)
  - [EURID Specification V1.2](https://www.enocean-alliance.org/wp-content/uploads/2021/03/EURID-v1.2.pdf)
  - [EEP V3.1 (high-level)](https://www.enocean-alliance.org/wp-content/uploads/2020/07/EnOcean-Equipment-Profiles-3-1.pdf)
  - [EEPViewer](https://tools.enocean-alliance.org/EEPViewer) (individual profiles)


## Copyright & license
Copyright 2026 Henning Kerstan

Licensed under the Apache License, Version 2.0 (the "License"). See [LICENSE](./LICENSE) file for details.
