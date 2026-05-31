# JBL Charge 5 — Verified Control Protocol

Empirically verified against a real JBL Charge 5 on **2026-05-31** (firmware as
shipped). Starting point was the public spec at
[pembem22/connect-plus #56](https://github.com/pembem22/connect-plus/discussions/56);
everything below was confirmed live on the device.

## Transport — **BLE GATT** (confirmed)

The Charge 5 advertises over BLE while powered on and exposes one custom service:

```
service  65786365-6c70-6f69-6e74-2e636f6d0000
  char   65786365-6c70-6f69-6e74-2e636f6d0001   notify, read   <- responses arrive here
  char   65786365-6c70-6f69-6e74-2e636f6d0002   write, write-without-response  <- send commands here
```

**Request and response use different characteristics.** Write a command frame to
`...0002`; the speaker answers via notifications on `...0001`.

No Bluetooth Classic / RFCOMM is needed. BLE discovery works without pairing.
This means a Home Assistant Bluetooth (`bleak`) integration can reach it natively.

> macOS note: running `bleak` from a plain Python aborts (TCC: missing
> `NSBluetoothAlwaysUsageDescription`). Recon was done with a copy of the
> Homebrew `Python.app` bundle, with that key added to its `Info.plist` and
> re-signed ad-hoc, launched via `open` (LaunchServices). On Linux (the HA
> target) there is no such restriction.

## Frame format (confirmed)

```
0xAA | packet_type | [length | payload...]
```
- Length byte + payload present only when there is a payload (e.g. request is just `AA 11`).
- No checksum.

| packet_type | meaning |
|-------------|---------|
| `0x11` | Speaker-Info request (sent to `...0002`) |
| `0x12` | Speaker-Info response (notified on `...0001`) |

## Speaker-Info exchange (confirmed)

Writing `AA 11` triggers a **burst of `0x12` notifications, one token each**.
Each `0x12` payload is `00 <token> [len] <value...>` (leading `00` observed on
every frame; its exact meaning — index/flags — is not yet pinned).

Real capture (battery was 100%):

| Raw frame | Token | Meaning | Value |
|-----------|-------|---------|-------|
| `aa120f00c10c4a424c204368617267652035` | `0xC1` | device name (len-prefixed, `0x0C`=12) | `"JBL Charge 5"` |
| `aa120400422040` | `0x42` | model id (2-byte) | `0x2040` |
| `aa1203004301` | `0x43` | color | `0x01` |
| `aa1203004464` | `0x44` | **battery %** (1-byte) | `0x64` = **100** |
| `aa1203004600` | `0x46` | audio channel | `0x00` (mono) |
| `aa1203004701` | `0x47` | audio source state | `0x00`=idle / `0x01`=BT source connected |
| `aa12080048aabbccddeeff` | `0x48` | **MAC** (6-byte, no len) | `aa:bb:cc:dd:ee:ff` |
| `aa1204004a1d9f` | `0x4A` | unknown (2-byte) | `0x1D9F` |

### Token value sizing (observed)
- 1-byte value: `0x43` color, `0x44` battery, `0x46` channel, `0x47` source.
- 2-byte value: `0x42` model, `0x4A` unknown.
- length-prefixed: `0xC1` device name (`<token> <len> <bytes>`).
- fixed 6-byte, no length: `0x48` MAC.

`tokens.extract_battery` does NOT rely on full TLV parsing — it scans for the
`0x44` marker and reads the next byte. Verified correct against the real
`00 44 64` frame (test `test_real_charge5_battery_capture`).

## Mapped to the user's asks

- **Battery level** — ✅ token `0x44`, confirmed 100% live.
- **Bluetooth id (MAC)** — ✅ token `0x48` = `aa:bb:cc:dd:ee:ff`.
- **Device name / model / color** — ✅ tokens `0xC1` / `0x42` / `0x43`.

## Open questions

- **Is it playing?** — ✅ Resolved (2026-05-31 differential capture). Token
  `0x47` = audio-source state: `0x00` when no BT source is connected (idle),
  `0x01` when a BT source is connected. It does NOT distinguish play vs pause —
  paused-but-connected still reports `0x01`. So `0x47` is a "source connected /
  in use" signal, not transport state. True play/pause is AVRCP-level between
  the phone and the speaker and is NOT exposed by this control protocol.
  Captures: `docs/captures/poll_state_idle.txt` (0x47=00),
  `poll_state_playing.txt` and the paused run (both 0x47=01).
- **Leading `00` byte** on each `0x12` payload — index vs flags, unconfirmed.
- **Token `0x4A`** (`0x1D9F`) — meaning unknown (serial? firmware? linked count?).
- Whether the protocol stays reachable while the speaker streams audio from a
  phone (i.e. can HA poll without interrupting playback) — to be tested.
