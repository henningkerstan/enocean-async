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

`Observable` members are stable string constants (`Observable.TEMPERATURE`, `Observable.ILLUMINATION`, `Observable.SWITCH_STATE`, `Observable.POSITION`, `Observable.COVER_STATE`, …). Each member carries its native unit as `Observable.TEMPERATURE.unit == "°C"`.

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
gateway.add_device(address=eurid, eep=EEP.from_string("D2-05-00"), name="Living room blind")
```

### Learning / teach-in
```python
await gateway.start_learning(timeout_seconds=60)
# Gateway accepts UTE teach-in (with automatic response); 4BS teach-in, and 1BS teach-in are NOT YET SUPPORTED
gateway.stop_learning()
```

### Gateway utilities
- Retrieve EURID, Base ID and firmware version info
- Change the Base ID
- Auto-reconnect: when the serial connection is lost, the gateway retries for up to 1 hour


## What works
- Full receive pipeline: raw serial bytes → ESP3 → ERP1 → EEP decode → observers → `Observation` callbacks
- Full send pipeline: typed `Instruction` → `EEPHandler.encode()` → ERP1 → ESP3 → serial
- Device registration with per-device EEP and observer instantiation
- Learning mode: UTE teach-in (query parsing + automatic bidirectional response)
- Auto-reconnect on connection loss
- EURID, Base ID, firmware version retrieval; Base ID change
- Parsing of all EEPs listed in [SUPPORTED_EEPS.md](SUPPORTED_EEPS.md)
- Sending instructions for: D2-05-00 (covers), D2-20-02 (fan), A5-38-08 (dim gateway), D2-01 (switches/dimmers)


## What is missing / not yet implemented
- ECID sub-dispatch for D2-01 extended commands
- More EEPs (contributions welcome — see [SKILLS.md](SKILLS.md) for the step-by-step guide)
- Logging coverage is partial
- 4BS teach-in, 1BS teach-in


## Implemented EEPs
See [SUPPORTED_EEPS.md](SUPPORTED_EEPS.md).


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
    ├── PushButtonObserver → reads values["R1"], values["EB"], … (stateful, hold timer)
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

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed description of the EEP layer, the semantics layer, and the key design decisions.


## Contributing
See [CONTRIBUTING](CONTRIBUTING.md).


## Versioning
See [VERSIONING.md](VERSIONING.md) for the version scheme and bump instructions.


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
