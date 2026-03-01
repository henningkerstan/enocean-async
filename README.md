# enocean-async
A light-weight, asynchronous, fully typed Python library for communicating with EnOcean devices over a USB gateway. Based on [pyserial-asyncio-fast](https://pypi.org/project/pyserial-asyncio-fast/) and the [EnOcean Serial Protocol Version 3 (ESP3)](https://www.enocean.com/wp-content/uploads/Knowledge-Base/EnOceanSerialProtocol3-1.pdf).

> **Note:** The API may still change (and even significantly!). Feedback and contributions are welcome.


## Features

### Receive pipeline — observables
Incoming radio telegrams are decoded into typed `StateChange` objects at the top of the pipeline. Callbacks are available at every stage for lower-level access:

```python
# Stage 4 — semantic: one StateChange per observable per device
gateway.add_state_change_callback(lambda sc: print(sc))
# StateChange(device_address=…, observable_uid='temperature', value=21.3, unit='°C', channel=None, …)

# Stage 3 — decoded EEP message (field values + semantic entities)
gateway.add_eep_message_received_callback(lambda msg: ..., sender_filter=eurid)

# Stage 2 — parsed ERP1 telegram (RORG, sender, raw payload bits)
gateway.add_erp1_received_callback(lambda erp1: ...)

# Stage 1 — raw ESP3 packet (before any parsing)
gateway.add_esp3_received_callback(lambda pkt: ...)
```

Observable UIDs are stable string constants defined in `ObservableUID` (`temperature`, `illumination`, `switch_state`, `position`, `cover_state`, `window_state`, `energy`, `power`, …). Multi-channel actuators include a `channel` field so individual outputs can be distinguished.

### Send pipeline — typed actions
Commands are sent to devices using typed `Action` objects:

```python
from enocean_async.capabilities.cover_actions import SetCoverPositionAction
from enocean_async.capabilities.action_uid import ActionUID

await gateway.send_command(destination=device_eurid, action=SetCoverPositionAction(position=75))
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
- Full receive pipeline: raw serial bytes → ESP3 → ERP1 → EEP decode → capabilities → `StateChange` callbacks
- Full send pipeline: typed `Action` → `EEPHandler.encode()` → ERP1 → ESP3 → serial
- Device registration with per-device EEP and capability instantiation
- Learning mode: UTE teach-in (query parsing + automatic bidirectional response)
- Auto-reconnect on connection loss
- EURID, Base ID, firmware version retrieval; Base ID change
- Parsing of all EEPs listed in [SUPPORTED_EEPS.md](SUPPORTED_EEPS.md)
- Sending commands for: D2-05-00 (covers), D2-20-02 (fan), A5-38-08 (dim gateway), D2-01 (switches/dimmers)


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
  .entities  {observable_uid → EntityValue} ← semantic vocabulary: "temperature", "illumination"
    │ Capability.decode()  (one call per capability in device.capabilities)
    ├── ScalarCapability(observable_uid=TEMPERATURE)  → reads entities["temperature"]
    ├── ScalarCapability(observable_uid=ILLUMINATION) → reads entities["illumination"]
    ├── CoverCapability     → reads entities["position"] + entities["angle"], infers "cover_state"
    ├── PushButtonCapability → reads values["R1"], values["EB"], … (stateful, no observable_uid)
    └── MetaDataCapability  → emits rssi, last_seen, telegram_count
    │ _emit()
    ▼
StateChange(device_address, observable_uid, value, unit, channel, timestamp, source)
    │ on_state_change callback
    ▼
Application
```

### Send pipeline (actions)

```
Application
    │ gateway.send_command(destination, action=SetCoverPositionAction(position=75))
    ▼
Action  (typed dataclass, action_uid class variable)
    │ EEPSpecification.command_encoders[action.action_uid](action)
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

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed description of the EEP layer, the capability layer, and the key design decisions.


## Contributing
See [CONTRIBUTING](CONTRIBUTING.md).


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
