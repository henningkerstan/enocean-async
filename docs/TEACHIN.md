# Teach-In Handling

This document describes the teach-in and teach-out behavior of enocean-async from a user and integrator perspective.

---

## Teach-In Types

| Type | RORG | Carries EEP? | Bidirectional? | Handling |
|------|------|-------------|---------------|---------|
| UTE  | 0xD4 | Yes (RORG + FUNC + TYPE) | Yes (ACK/NAK required) | Auto-response + registration → `NewDeviceCallback` + `DeviceTaughtInCallback` |
| 4BS with profile | 0xA5, LRN=0, LT=1 | Yes (A5-FUNC-TYPE) | Yes (always sent by gateway) | Auto-registration + response → `NewDeviceCallback` + `DeviceTaughtInCallback` |
| 4BS profileless  | 0xA5, LRN=0, LT=0 | No | No | Logged, ignored → `NewDeviceCallback` only |
| 1BS  | 0xD5 | No | No | Logged, ignored → `NewDeviceCallback` only |
| RPS  | 0xF6 | No | No | Not applicable (no teach-in mechanism) |

---

## API

```python
# Fires after successful teach-in and device registration
type DeviceTaughtInCallback = Callable[[EURID, EEP], None]

gateway.add_device_taught_in_callback(lambda address, eep: ...)

await gateway.start_learning(
    timeout=30,           # session ends automatically after this many seconds
    allow_teach_out=False,# if True, teach-out requests are honored during this session
    sender_id=None,       # sender for UTE responses; defaults to gateway base ID
)

gateway.stop_learning()   # end session early
```

Both teach-in and teach-out require an active learning session.

### Relationship to `NewDeviceCallback`

- `NewDeviceCallback(eurid)` — fires on the first telegram received from any unknown EURID, before any EEP is known.
- `DeviceTaughtInCallback(address, eep)` — fires only after a successful teach-in, once the device has been registered with its EEP. This is the pairing signal.

For UTE and 4BS-with-profile, both callbacks fire for the same device: `NewDeviceCallback` first (on the teach-in telegram itself), then `DeviceTaughtInCallback` once registration is confirmed.

---

## UTE Teach-In

The gateway only processes UTE teach-in telegrams during an active learning session. Outside of learning mode, UTE messages are still forwarded to raw UTE callbacks but otherwise ignored.

```
Device presses teach button → sends UTE query (TEACH_IN)
    │
    ├─ EEP not supported?
    │   └─ respond NOT_ACCEPTED_EEP_NOT_SUPPORTED
    │
    ├─ device already registered? (re-teach-in)
    │   └─ reuse previously allocated sender address
    ├─ addressed device (VLD)?
    │   └─ no sender slot needed — BaseID+0 is shared
    └─ sender-addressed?
        └─ allocate next free sender slot (BaseID+1 … +127)
    │
    ├─ respond ACCEPTED_TEACH_IN  (carrying the chosen sender address)
    ├─ register device
    └─ fire DeviceTaughtInCallback
```

---

## UTE Teach-Out

Teach-out is only possible via UTE, and only during an active learning session started with `allow_teach_out=True`. Two request types trigger the teach-out path:

- `TEACH_IN_DELETION` — explicit unpair request from the device.
- `TEACH_IN_OR_DELETION_OF_TEACH_IN` — toggle: the device doesn't know its own pairing state and asks the gateway to decide.

```
TEACH_IN_OR_DELETION_OF_TEACH_IN:
    ├─ device is registered → treat as teach-out (see below)
    └─ device is not registered → treat as teach-in (normal path above)

TEACH_IN_DELETION  (or teach-out path from toggle):
    ├─ teach-out not allowed?
    │   └─ respond NOT_ACCEPTED_GENERAL_REASON
    ├─ device not registered?
    │   └─ respond NOT_ACCEPTED_GENERAL_REASON
    └─ device registered + teach-out allowed:
        ├─ deregister device
        └─ respond ACCEPTED_DELETION_OF_TEACH_IN
```

For the toggle case, sending `ACCEPTED_TEACH_IN` when the device is already registered would be wrong — the device would believe it freshly re-paired. The gateway NAKs instead.

### Symmetric model

Teach-out requires the same active learning session as teach-in. This is a deliberate security choice:

| | Symmetric (implemented) | Asymmetric (not implemented) |
|---|---|---|
| Security | Higher — a rogue telegram cannot unpair a device | Lower — any `TEACH_IN_DELETION` could unpair |
| UX | User must start a session with `allow_teach_out=True` to unpair | Pressing the device button always unregisters |

---

## 4BS Teach-In

4BS teach-in is bidirectional — the gateway always sends a response. The `learn_status` field (bit 27 of DB0) guards against processing loopback: if `learn_status=RESPONSE` (1), the telegram is a response from another gateway and is discarded. All `QUERY` (0) telegrams are processed and acknowledged — devices that do not require a response simply ignore it.

```
Device sends 4BS teach-in telegram (LRN=0)
    │
    ├─ not in learning mode → discard (no response)
    ├─ learn_status == RESPONSE → discard (gateway only processes queries)
    ├─ profileless (no EEP in telegram) → log + discard (no response)
    │
    ├─ device already registered with same EEP? (re-teach-in, no change)
    │   └─ respond ACCEPTED / SENDER_ID_STORED
    │
    ├─ device already registered with different EEP? (EEP change)
    │   ├─ check new EEP is supported
    │   │   └─ if not → log + discard (no response)
    │   ├─ update device EEP in registry
    │   └─ respond ACCEPTED / SENDER_ID_STORED
    │
    ├─ EEP not supported → log + discard (no response)
    │
    ├─ addressed device? → no sender slot needed (use BaseID+0)
    └─ sender-addressed? → allocate next free sender slot (BaseID+1…+127)
    │
    ├─ register device
    ├─ respond ACCEPTED / SENDER_ID_STORED
    └─ fire DeviceTaughtInCallback
```

The response echoes the EEP (FUNC, TYPE, manufacturer) back to the device with result bits indicating EEP support (`FourBSEEPResult`) and whether the sender ID was stored (`FourBSTeachInResult`).

---

## Sender Address Allocation

EnOcean devices fall into two categories from the gateway's sending perspective:

| Category | Examples | How device filters commands |
|---|---|---|
| **Destination-addressed** (VLD) | D2-xx | By destination address field — multiple devices share the same sender (BaseID+0) |
| **Sender-addressed** | A5-38, A5-20 | Learns the gateway's sender address at teach-in; ignores all other senders |

The gateway has 128 available sender addresses:

```
BaseID+0        →  shared sender for all addressed devices
BaseID+1…+127   →  one dedicated slot per sender-addressed device
```

The used slots are derived on demand from the live device registry — no separate tracking structure is needed. The lowest free offset is always assigned to a new device.

Rules:
- **New teach-in**: assign the lowest free slot.
- **Re-teach-in** of a known device: reuse the existing slot — no reallocation.
- **Device removal**: the slot is freed automatically.
- **Pool exhaustion** (> 127 broadcast devices): the teach-in is rejected with an error.

### Persistence

Sender-addresseds must have their sender address persisted by the caller and restored on startup:

```python
gateway.add_device(
    address=EURID(stored["eurid"]),
    eep=EEP.from_string(stored["eep"]),
    sender=BaseAddress(stored["sender"]),  # None for addressed devices
)
```

Persisting the full address (not a bare offset) avoids ambiguity if the base ID ever changes.
