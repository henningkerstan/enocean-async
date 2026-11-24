# Plan: secure telegrams (experimental)

Status: **draft — decisions in section 3 to be confirmed before implementation**
Branch: `feature/secure-telegrams`
Reference: *Security of EnOcean Radio Networks*, V4.03 (EnOcean Alliance, 2023). Not committed to the repository (licence); section and annex numbers below refer to this version.

## 1. Goal and scope

Receive, decrypt and authenticate secure ERP1 telegrams in software, as an opt-in experimental feature. Devices without a security context behave exactly as today.

**In scope (v1, receive-only)**

- Security modes: VAES with CMAC (legacy, most deployed devices) and CCM (§4.1, §7)
- All SLF values of Table 3 plus the legacy values of Annex C (VAES encodings are bit-compatible)
- Rolling code (RLC) handling: full, reduced (§6.3.3.2) and implicit with a window of 128 (§6.3.3.3), including legacy 16-bit RLC with rollover
- Secure R-ORGs: `SEC` 0x30 (PTM switches, no R-ORG), `SEC_R` 0x31 (with encrypted R-ORG), `SEC_CDM` 0x33 (chained), `SEC_TI` 0x35 (security teach-in, 2 telegrams, optional PSK)
- Unidirectional security teach-in during a learning session, followed by the regular UTE/4BS teach-in inside the secure channel
- EEP `D2-03-00` (secure rocker data of PTM 21x switches, see Annex A.1)

**Out of scope (v1)**

- Sending secure telegrams, bidirectional security teach-in (needs actuator hardware; the 500 ms response deadline of §5.3.3.2 needs a send path that can bypass the send lock queue)
- `SEC_MAN` 0x34, `SEC_DAT` 0x36, ERP2, key derivation (§7.6)
- ESP2 modules (their protocol only carries RPS/1BS/4BS telegrams)
- Module-side decryption via ESP3 secure-device commands

## 2. Architecture

### 2.1 Receive path

#### What a secure telegram encapsulates

A secure telegram is an envelope around the R-ORG and DATA of a plain telegram. SENDER ID, STATUS and the ESP3 optional data (destination, RSSI, sub-telegram count) are **not** encrypted; they belong to the envelope and are copied to the decrypted telegram. Example from Annex A.2.3.3 (4BS sensor, VAES, SLF 0xAB):

```
received (ERP1):   31 | 3E EA C4 A2 DF | C0 FF EE | EA F2 0E | <sender> | <status>
                   │    │                │          │
                   │    │                │          └ MAC (3 bytes)
                   │    │                └ RLC (3 bytes)
                   │    └ encrypted R-ORG + DATA
                   └ R-ORG-S SEC_R
decrypted:         A5 | 08 27 FF 80     | <sender> | <status>    → a plain 4BS telegram (here: a teach-in, LRN bit 0)
```

| Envelope | Encrypted content | Result of unwrapping |
|---|---|---|
| `SEC_R` 0x31 | R-ORG + DATA | plain telegram with the inner R-ORG (A5, D2, D4 UTE, …) |
| `SEC_CDM` 0x33, ×N | segments of one `SEC_R` payload (2-byte length in the first segment) | as `SEC_R`, once all segments are in; envelope = all N telegrams |
| `SEC` 0x30 | DATA only (no R-ORG, used by PTM switches) | telegram with R-ORG `SEC_D` 0x32, as defined by the spec (§2.5.3); decoded with the device's registered EEP (`D2-03-00`) — EEP dispatch already selects the profile by device, not by R-ORG |
| `SEC_TI` 0x35, ×2 | no telegram; carries SLF, RLC and key (key optionally PSK-encrypted) | no inner telegram — a security teach-in event |

Addressed telegrams: the ESP3 module delivers the destination in the optional data, as for plain telegrams. Whether a module also strips an ADT wrapper (0xA6) around a secure telegram is to be verified with hardware; if not, unwrap ADT before the step below.

#### Exact flow in `__process_erp1_telegram`

```
ESP3 RADIO_ERP1 packet
 1  ERP1Telegram.from_esp3()                     new R-ORGs parse instead of failing
 2  own-echo check, repeater de-duplication      unchanged; runs on the envelope, so a repeated copy
                                                 never reaches the RLC check (no false replay alarms)
 3  telegrams_received += 1                      counts radio telegrams, i.e. envelopes
 4  emit ERP1 callbacks (envelope)               unchanged: every radio telegram as received
 5  new-device detection                         unchanged
 6  R-ORG is SEC_TI?
      not learning → drop (debug log)
      learning     → SecureTeachInReassembler (per sender) → on second telegram: decrypt key with PSK
                     if flagged → pending SecurityContext (see D5) → stop
 7  R-ORG is SEC_CDM?
      → ChainReassembler (per sender + CHAIN_ID); incomplete → stop; complete → continue as SEC_R
 8  R-ORG is SEC / SEC_R?
      context = device.security, or the pending teach-in context of this sender
      no context → drop (debug log), stop
      SecurityProcessor.unwrap(envelope(s), context):
        split fields per SLF → reconstruct RLC → decrypt → verify MAC
        failure  → telegrams_rejected += 1, debug log with reason, stop
        success  → context.next_rlc = rlc + 1
                   emit security-state callback (address, context)
                   inner = ERP1Telegram(inner R-ORG, data, envelope sender/status/optional data,
                                        security=SecurityInfo(envelope, slf, rlc))
 9  emit ERP1 callbacks (inner)                  second emission, see D3
10  plain telegram from a device that has a context, and no learning session → reject (D4), stop
11  existing dispatch on the (inner) telegram:   UTE → UTE handler; 4BS with LRN → 4BS teach-in;
                                                 otherwise EEP decoding → observers
```

Steps 1–5 and 11 are today's code; steps 6–10 are new and only act on secure R-ORGs or on devices with a context. Keys never appear in logs or `repr`.

### 2.2 Module layout

```
enocean_async/experimental/__init__.py
enocean_async/experimental/security/
    __init__.py         public experimental API (SecurityContext, SecurityLevelFormat, errors)
    slf.py              SecurityLevelFormat: parse/encode SLF byte, legacy + V4 encodings
    crypto.py           vaes_crypt(), cmac(), ccm_decrypt()/ccm_encrypt(), lazy `cryptography` import
    rlc.py              reconstruct_rlc() for full / reduced / implicit (window) modes
    context.py          SecurityContext dataclass (key hidden from repr, slf, next_rlc, is_ptm)
    telegram.py         field parsing for SEC / SEC_R / SEC_TI, SEC_CDM chain reassembly
    teach_in.py         SEC_TI two-telegram reassembly, PSK decryption → SecurityContext
    processor.py        SecurityProcessor.unwrap(): the one entry point the gateway calls
enocean_async/eep/d2/d2_03_00.py   secure rocker EEP (button entities, reuse button observer logic)
```

Encrypting functions (`vaes_crypt` is symmetric, `ccm_encrypt`) are included because the tests need them to build telegrams and bidirectional support will need them later; the gateway does not send secure telegrams in v1.

### 2.3 Changes to existing code

| File | Change |
|---|---|
| `protocol/erp1/rorg.py` | add `RORG_SEC` 0x30, `RORG_SEC_R` 0x31, `RORG_SEC_D` 0x32, `RORG_SEC_CDM` 0x33, `RORG_SEC_TI` 0x35 |
| `protocol/erp1/telegram.py` | length validation for the new R-ORGs; `security: SecurityInfo \| None = None` field on `ERP1Telegram` (D3) |
| `device.py` | `security: SecurityContext \| None = None` |
| `gateway.py` | `add_device(..., security=)`, `set_device_security()`, `add_security_state_callback()`, unwrap step in `__process_erp1_telegram`, SEC_TI handling in learning mode, `telegrams_rejected` counter |
| `pyproject.toml` | optional extra `security = ["cryptography>=…"]` |
| `eep/__init__.py`, `eep/device_type.py` | register `D2-03-00`, add PTM 215-based products if known |
| docs | `docs/SECURITY.md` (usage, guarantees and non-guarantees), `TEACHIN.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, README note |

## 3. Decisions

Each has a proposal; confirm or change before implementation.

**D1 — Where security state lives.**
Proposal: `SecurityContext` on `Device`, passed via `add_device(..., security=SecurityContext(...))` and replaceable via `set_device_security(address, ctx | None)`. Keeps the library stateless with respect to storage, like device config today.

**D2 — How state is persisted.**
Proposal: `add_security_state_callback(cb: Callable[[DeviceAddress, SecurityContext], None])`, fired after every successful authentication (RLC advanced) and after secure teach-in. The integration persists, debounced. Crash semantics, documented: if the persisted RLC lags behind, telegrams in that gap could be replayed once; a stored RLC can never be ahead of the device. A repeated security teach-in with the same key resets the RLC (§6.3.2), which is the recovery path.
Alternative: a storage protocol the integration implements (more coupling, no benefit for HA).

**D3 — What ERP1 callbacks see.**
Proposal: the same ERP1 callbacks fire twice for an authenticated secure telegram — once for the envelope as received (step 4), once for the decrypted inner telegram (step 9). For a `SEC_CDM` chain: N envelope emissions, then one inner emission.

Why the same callback and not a new one:
- It matches the protocol layering: the spec itself models the result of security processing as a new telegram handed up to the application (`SEC_D` for `SEC`, the original R-ORG for `SEC_R`, §2.5.3).
- The two emissions cannot be confused: the envelope has a secure R-ORG (0x30/0x31/0x33/0x35), the inner one a plain R-ORG and `security` set. Existing consumers that switch on R-ORG ignore the envelope and handle the inner telegram without changes; a serial monitor shows both, which is what one wants when debugging.
- Callbacks stay 1:1 with *telegrams*, each at its layer, instead of mixing both into one object.

What it requires:
- `ERP1Telegram.security: SecurityInfo | None` — `None` for anything received over the air as is; set only on telegrams the library authenticated. `SecurityInfo` holds the envelope telegram(s), SLF and RLC (no key). Plus an `is_authenticated` property.
- Documented semantics: the ERP1 callback delivers every radio telegram **unfiltered and untrusted**, including spoofed plain telegrams for a secure device (they are rejected only at step 10); only telegrams with `security` set are authenticated. `telegrams_received` counts envelopes, not inner telegrams.
- `EEPMessage` carries the same information (e.g. `authenticated: bool`) for integrations working above the ERP1 layer.

Alternatives considered:
- *Envelope only* (no second emission): ERP1-level consumers can never see decrypted content; debugging needs extra logging.
- *Inner only*: hides what was actually received, so rejected envelopes (MAC failure, replay) become invisible at ERP1 level.
- *Separate `add_decrypted_erp1_callback`*: no behaviour change for existing consumers, but a second API for the same thing; consumers that want "all telegrams, decrypted where possible" have to register twice and merge.

**D4 — Strictness.**
Proposal: a device with a security context accepts only telegrams that authenticate; plain telegrams from it are rejected (otherwise an attacker sends unencrypted ones). Exception: `SEC_TI` and plain teach-in telegrams during a learning session focused on or open to that device. A secure telegram from a device without a context is dropped as today, with a debug log.

**D5 — Teach-in hand-over.**
Proposal: after a complete `SEC_TI`, the gateway stores a pending context for that sender for the rest of the learning session.
- PTM (TYPE bit set): register directly as `D2-03-00` with the context, fire `DeviceTaughtInCallback` and the security-state callback.
- Non-PTM: the device follows with a secure UTE/4BS teach-in; it is unwrapped with the pending context and handled by the existing teach-in code, which registers the device with the context attached. If the session ends first, the pending context is discarded (§8.3.5).
`DeviceTaughtInCallback` keeps its signature; the key reaches the integration only via the security-state callback.

**D6 — PSK.**
Proposal: `start_learning(for_device=eurid, psk=bytes)`. A PSK is per device, so it is only accepted for a focused session; `SEC_TI` with the PSK flag outside such a session is rejected with a log message naming the reason.

**D7 — API surface.**
Proposal: everything public lives in `enocean_async.experimental.security`; gateway methods taking security arguments are documented as experimental. The API may change in minor releases while experimental (stated in CHANGELOG and `docs/SECURITY.md`). `cryptography` is imported lazily; using security without the extra raises `ImportError` with an install hint.

## 4. Implementation steps

Each step is one commit with its tests passing.

1. **Crypto core** — `slf.py`, `crypto.py`, `rlc.py`, optional extra. Tests: Annex A VAES/CMAC and CCM steps for A.1 (PTM), A.2 (4BS), A.3 (chained VLD with UTE), all intermediate values (K1/K2, AES outputs) not just end results; RLC examples 1 and 2 of §6.3.3.2; implicit window; 16-bit rollover; all Table 3 and Annex C SLF values.
2. **Telegram parsing** — R-ORGs, `telegram.py`, `teach_in.py`. Tests: A.1.2 / A.2.2 / A.3.2 SEC_TI telegrams in both modes, PSK variants, SEC_CDM reassembly (A.3), out-of-order and incomplete chains, malformed lengths.
3. **Processor** — `context.py`, `processor.py`. Tests: A.x resulting telegrams decrypt to the plain data; MAC mismatch, replay, RLC below accepted, wrong key; RLC advances only on success.
4. **Gateway integration** — D1–D4, D7. Tests: ESP3 packets from Annex A through a gateway with a registered secure device produce the expected observations; rejection cases; security-state callback; repeater copy not counted as replay; device without context unchanged.
5. **Secure teach-in in learning mode** — D5, D6. Tests: PTM teach-in registers `D2-03-00`; SEC_TI + secure UTE registers the VLD device with context; pending context discarded at session end; PSK only in a focused session.
6. **`D2-03-00` EEP** — button entities; verify the data mapping against the EEP specification (Annex A.1 only shows `0B` = B1 pressed).
7. **Docs** — `docs/SECURITY.md`, `TEACHIN.md`, `ARCHITECTURE.md`, CHANGELOG (marked experimental), README.

## 5. Testing beyond unit tests

- One hardware session with a secure device (ideally a PTM 215-based switch plus one secure sensor): teach-in, normal use, restart with persisted state, re-teach-in.
- Ask testers for raw ESP3 captures together with the key of a test device; each capture becomes a regression test.
- Debug logging of rejections must be specific enough (SLF, RLC mode, reason) to diagnose a report without the key.

## 6. Open questions

- Which secure devices are available for testing?
- Does HA need anything from `DeviceSpec` to show that a device is secure (e.g. a diagnostic entity "secure: yes")?
- Should `telegrams_rejected` be a gateway observable (like `telegrams_received`) or only a log/debug counter?
