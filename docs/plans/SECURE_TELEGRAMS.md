# Plan: secure telegrams (experimental)

Status: **decisions confirmed (section 3); ready for implementation of stage 1**
Branch: `feature/secure-telegrams`
References (not committed to the repository, licence):
- *Security of EnOcean Radio Networks*, V4.03 (EnOcean Alliance, 2023); section and annex numbers below refer to this version.
- *PTM 210 / PTM 215 / PTM 215U / PTM 215J User Manual*, step code DC, March 2022 (EnOcean); cited as "PTM manual".
- Application note AN509 *Overview of EnOcean Security features* (referenced by the PTM manual for worked examples).

Test hardware: one **PTM 215** (868 MHz, ERP1), see section 1.1.

## 1. Goal and scope

Receive, decrypt and authenticate secure ERP1 telegrams in software, as an opt-in experimental feature. Devices without a security context behave exactly as today.

The work is split into two stages. Stage 1 is everything a PTM 215 needs, end to end, so that it can be tested on the hardware at hand before anything is built that only the specification can test. Stage 2 adds the parts no available device uses; it reuses the stage 1 core and is tested against Annex A only.

**Stage 1 (PTM 215, receive-only)**

- Security mode VAES with CMAC (the PTM uses nothing else)
- SLF values of the two PTM modes (section 1.1) plus parsing of all SLF values of Table 3 and Annex C, so that an unsupported one is rejected with a clear reason
- RLC: explicit 24-bit (transmitted) and implicit 16-bit (not transmitted) with a window of 128 (§6.3.3.3), including the 16-bit rollover
- Secure R-ORGs `SEC` 0x30 (data) and `SEC_TI` 0x35 (security teach-in, 2 telegrams, key unencrypted)
- Security teach-in of a PTM during a learning session; alternatively adding a PTM with the key from its label (D8)
- EEP `D2-03-00` (secure rocker data, Annex A.1)

**Stage 2 (no test device, Annex A only)**

- CCM (§4.1, §7)
- `SEC_R` 0x31 (with encrypted R-ORG), `SEC_CDM` 0x33 (chained), reduced RLC (§6.3.3.2)
- PSK-encrypted keys in `SEC_TI` (D6)
- Hand-over from the security teach-in to a secure UTE/4BS teach-in of a non-PTM device (D5)

### 1.1 PTM 215 facts (PTM manual)

| | |
|---|---|
| Delivery state | normal mode: plain RPS (`F6-02-01` etc.), as supported today (§3) |
| Secure mode, explicit RLC (recommended) | entered with the **3-nipple** special button combination (SBC); SLF: VAES, 24-bit MAC, 24-bit RLC, RLC transmitted (§3.2.2, §3.2.3) |
| Secure mode, implicit RLC (legacy, 868 MHz only) | entered with the **2-nipple** SBC; SLF: VAES, 24-bit MAC, 16-bit RLC, RLC not transmitted (§3.2.1, §3.2.3) |
| Back to normal mode / factory reset | 4-nipple SBC with 1 press / with 7 presses of the energy bow (§3.3, §3.4) |
| Data telegram | R-ORG `SEC` 0x30, EEP `D2-03-00`, 2 redundant sub-telegrams (§4.2.2, §4.3) |
| Security teach-in | SBC held, energy bow pressed and released twice: switches the mode and sends the first part on the 2nd press, the second part on the 2nd release; once in secure mode, a single press/release sends both parts. One sub-telegram per part, no redundancy (§3.2.3, Table 3). `TEACH_IN_INFO`: type 1 = PTM, info 0 = rocker A / 1 = rocker B (the channel whose two nipples were pressed). No PSK mentioned. |
| Key | random, device-specific factory key, also in the label's QR code (container `13Z`, 32 hex digits) and in the NFC NDEF string (§5.3.4.7, labelling). A user key can be written via NFC (write-only); this resets the RLC to 0. A factory reset returns to the factory key but keeps its RLC. |
| RLC | starts at 0 at production, +1 per telegram (§3.2) |

Consequences for the plan:
- The PTM is usable with the library today in normal mode; secure mode is opt-in on the device as well.
- Explicit RLC is the mode to test first: no window search, and the key from the label suffices to decode telegrams even without a teach-in (D8).
- A test capture made with the factory key compromises this switch permanently, as the factory key cannot be changed without NFC (D9).

**Out of scope**

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
        failure  → telegrams_not_authenticated += 1, debug log with reason, stop
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
enocean_async/security/
    __init__.py         public API, experimental (SecurityContext, SecurityLevelFormat, errors)
    slf.py              SecurityLevelFormat: parse/encode SLF byte, legacy + V4 encodings
    crypto.py           vaes_crypt(), cmac(), ccm_decrypt()/ccm_encrypt(), based on `cryptography`
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
| `gateway.py` | `add_device(..., security=)`, `set_device_security()`, `add_security_state_callback()`, unwrap step in `__process_erp1_telegram`, SEC_TI handling in learning mode, `telegrams_not_authenticated` counter and gateway entity |
| `pyproject.toml` | dependency `cryptography>=…` |
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
Stage 1 implements the PTM branch only; the non-PTM branch is stage 2.

Confirmed details (stage 1):
- `SEC_TI` is processed only during a learning session and respects `for_device`. Part 1 (`IDX=0`) is kept per sender until part 2 (`IDX=1`) arrives or the session ends; a new part 1 replaces an old one; a part 2 without part 1 is dropped. `INFO` (rocker A/B, "normal teach-in", §8.3.3.2) is only logged: `D2-03-00` reports all four buttons.
- Unknown sender: register as `D2-03-00` with the context.
- Registered sender, same key: only the RLC is set to the teach-in value (§6.3.2), no new registration.
- Registered sender, different key or no context (e.g. a PTM registered as plain `F6-02-01` and switched to secure mode): the registration is changed to `D2-03-00` with the new context, as a 4BS re-teach-in with another EEP does today (`__change_device_type`, then `DeviceTaughtInCallback` for the known address). Address, name and sender stay; a catalog device type falls back to the generic one.
- Order of callbacks: security-state callback first, then `DeviceTaughtInCallback`, so that an integration re-adding the device already has the context.
- No teach-out via `SEC_TI`, even with `allow_teach_out`.
- The HA integration does not handle `DeviceTaughtInCallback` for a known address yet; it is to be added there (it is needed for 4BS re-teach-in as well).

**D6 — PSK (stage 2).**
The PTM manual mentions no PSK (its QR code holds the device key itself), so stage 1 rejects a `SEC_TI` with the PSK flag, with a log message naming the reason.
Direction for stage 2 (details to be decided then): the PSK is used for the session only and not stored. With VAES the PSK-encrypted RLC and key are not authenticated (§8.3.6), so a wrong PSK gives a wrong key without an error; the first data telegram that fails after a PSK teach-in is logged with "PSK wrong?". Pre-registered PSKs (`gateway.add_psk()`, also for open sessions) only if a device needs it.
Proposal for stage 2: `start_learning(for_device=eurid, psk=bytes)`. A PSK is per device, so it is only accepted for a focused session; `SEC_TI` with the PSK flag outside such a session is rejected with a log message naming the reason.

**D7 — API surface.**
Decided: everything public lives in `enocean_async.security`, marked experimental in its docstrings, `docs/SECURITY.md` and the CHANGELOG; gateway methods taking security arguments are documented as experimental. No `experimental` package: the gateway methods could not live in it anyway, and leaving it later would be a breaking import change. While experimental, the security API may change in minor releases; everything else keeps the usual rules.
`cryptography` becomes a regular dependency (no optional extra, no lazy import): simpler, and Home Assistant ships it anyway. AES is not implemented in Python.

**D8 — Adding a PTM with the key from its label.**
The key of a PTM 215 is printed in its QR code (and readable via NFC), so a switch can be added without a security teach-in, e.g. when it is out of reach of the gateway or the teach-in telegrams (no redundancy) keep getting lost.
Decided, following the out-of-band device setup of §6.3.2 (RLC_R starts at 0; the same key shall not be used more than once for it):
- `SecurityContext.from_label(text)` parses the labelling string (`30S` radio ID, of which the lower 32 bits are the EURID, and `13Z` key) and returns `(eurid, context)`; `SecurityContext.for_ptm(key)` does the same for a key without a label (a user key written via NFC). Both use the explicit-RLC SLF of the PTM and RLC_R = 0.
- Explicit RLC only: with implicit RLC the receiver cannot know the counter without the teach-in.
- The integration registers the switch as `D2-03-00` with `add_device(eurid, device_type, security=context)`.
- Factory key: the switch's counter is usually far above 0, so a recorded older telegram is accepted once if it arrives before any newer one. Documented; a later security teach-in closes the gap (D5). Adding the same switch by label again is what §6.3.2 advises against.
- User key written via NFC: the PTM resets its RLC to 0 (PTM manual §5.3.4.7), so RLC_R = 0 is exact and there is no gap. The PTM's NFC memory does not expose the RLC.
- Recommended order in the docs: NFC user key or security teach-in, then label key.

**D9 — Captures and keys in the repository.**
A capture is only useful as a regression test together with its key, and a test committed with the factory key compromises that switch for good (the factory key is fixed; a factory reset returns to it).
Decided (an NFC writer is available):
- The key of Annex A.1 (`8E 02 D4 9A 10 C1 AE 40 45 B5 99 C2 9A 05 A2 7C`; A.1 is a PTM with SLF `0xAB`, the PTM's explicit-RLC mode) is written to the PTM 215 as its user key via NFC. The key is published, and writing it resets the RLC to 0.
- The captures of section 5 are made with this key and committed under `tests/captures/` (raw ESP3 frames as hex, with a note on what was pressed). The switch's EURID in them is harmless; it is broadcast with every telegram.
- Afterwards a factory reset (4-nipple SBC, 7 presses) returns the switch to its factory key and discards the user key.
- No captures with the factory key in the repository, no local capture folder. The label route of D8 (factory key, RLC not at 0) is tested on hardware only; parsing the label string is unit-tested with the example of the PTM manual.

## 4. Implementation steps

Each step is one commit with its tests passing.

**Stage 1 (PTM 215)**

1. **Crypto core** — `slf.py`, `crypto.py` (VAES, CMAC), `rlc.py` (explicit, implicit with window), `cryptography` dependency. Tests: the Annex A.1 VAES/CMAC steps with all intermediate values (K1/K2, AES outputs), not just end results; implicit window; 16-bit rollover; parsing of all Table 3 and Annex C SLF values, with the two PTM SLFs accepted and the others rejected with a reason.
2. **Telegram parsing** — R-ORGs `SEC` and `SEC_TI` (the others added to the enum as well, so that they parse and are dropped instead of raising "Unknown RORG"), `telegram.py`, `teach_in.py`. Tests: A.1.2 `SEC_TI` in both RLC modes, part 2 before part 1, lost part, malformed lengths, PSK flag rejected.
3. **Processor** — `context.py`, `processor.py`. Tests: A.1 telegrams decrypt to the plain data; MAC mismatch, replay, RLC below accepted, wrong key; RLC advances only on success; the second sub-telegram of a press is not a replay alarm.
4. **`D2-03-00` EEP** — the EEP specification (2.6.8) gives the rocker nibble and its mapping to `F6-02-01` data/status, so the existing button observer can be reused: decode to the same `a0`/`a1`/`b0`/`b1` entities and button events as `F6-02-01`. Device catalog: the PTM 215 (in secure mode).
5. **Gateway integration** — D1–D4, D7, D8. Tests: ESP3 packets built from A.1 through a gateway with a registered secure device produce the expected observations; rejection cases; security-state callback; repeater copy not counted as replay; device without context unchanged; a device added from a label string.
6. **PTM security teach-in in learning mode** — D5 (PTM branch). Tests: both parts register `D2-03-00` with the context; one part only registers nothing; a security teach-in of a registered PTM replaces its context and RLC.
7. **Hardware session with the PTM 215** — see section 5. Fixes go into steps 1–6 as further commits; captures become regression tests (D9).
8. **Docs** — `docs/SECURITY.md` (including the button combinations of section 1.1), `TEACHIN.md`, `ARCHITECTURE.md`, CHANGELOG (marked experimental), README. Stage 1 can be released here.

**Stage 2 (Annex A only)**

9. **CCM** — Annex A CCM steps.
10. **`SEC_R`, `SEC_CDM`, reduced RLC** — A.2 (4BS), A.3 (chained VLD with UTE), RLC examples 1 and 2 of §6.3.3.2, out-of-order and incomplete chains.
11. **PSK** — D6, PSK variants of A.x.2.
12. **Non-PTM teach-in hand-over** — D5: `SEC_TI` + secure UTE registers the VLD device with context; pending context discarded at session end.

## 5. Testing on hardware (PTM 215)

Run with `examples/serial_monitor.py` (raw ESP3 frames) and a small script that registers the switch:

1. Normal mode: check that the switch works as `F6-02-01` today (baseline, and its EURID).
2. 3-nipple SBC (explicit RLC): security teach-in in a learning session; presses and releases of all four buttons; a second press within the redundancy window; restart with the persisted context.
3. Same switch added with the label string instead (D8), after removing it.
4. 2-nipple SBC (implicit RLC): teach-in, then presses with the gateway switched off in between (counter ahead, within the window).
5. Replay: send a captured telegram again; it must be rejected.
6. 4-nipple SBC: back to normal mode; the registered secure device now rejects the plain telegrams (D4) until it is removed or set to plain.

Debug logging of rejections must be specific enough (SLF, RLC mode, reason) to diagnose a report without the key.

## 6. Open questions

- ~~Secure indicator in `DeviceSpec`~~: no. Being secure is a property of the registration (`Device.security is not None`), not of the EEP; the integration can show it as a device attribute or build its own entity.
- ~~Counter of rejected telegrams~~: a gateway observable and diagnostic entity `telegrams_not_authenticated`, like `telegrams_received`. It counts telegrams that a device with a security context refuses: MAC mismatch, RLC below the accepted one (replay), no RLC within the window, a plain telegram from a secure device (D4). Not counted: repeated copies and own echoes, unknown devices, secure telegrams from a device without a context, parse errors, rejected teach-ins (logged only). The reason of each rejection goes to the debug log only.
- ~~Meaning of `TEACH_IN_INFO` rocker A/B~~: the rocker used to trigger the teach-in (§8.3.3.2), only logged (D5).
- ~~NFC writer~~: available (D9).
- ~~Security specification~~: published by the EnOcean Alliance, https://www.enocean-alliance.org/wp-content/uploads/2023/04/Security-of-EnOcean-Radio-Networks-V4.03.pdf
