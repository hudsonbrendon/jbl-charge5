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

## Live verification (2026-10-24)

Opcodes taken from the JBL Portable APK ([APK_PROTOCOL.md](APK_PROTOCOL.md)) and
sent to a real Charge 5 (firmware `0.8.6.0`). Requests carry a length byte, as
the app sends them (`AA 41 00`); `AA EE 01 <op> 00` means "unsupported".

| Request | Reply | Meaning | Used by the integration |
|---|---|---|---|
| `AA 11 00` | `AA 12 …` per token | Speaker info (below) | every poll |
| `AA 13 02 00 <tok>` | `AA 12 …` | One token only | — |
| `AA 41 00` | `AA 42 04 00 08 06 00` | Firmware, bytes as decimals → `0.8.6.0` | sensor |
| `AA 65 00` | `AA 66 01 <00/01>` | Feedback tones off/on | switch state |
| `AA 67 01 <00/01>` | `AA 00 02 67 00` | Set feedback tones | switch |
| `AA 6C 01 00` | `AA 6D 12 …` (2 notifications) | Simple EQ, see below | select + numbers |
| `AA 6E …` | `AA 00 02 6E 00` | Set simple EQ | select + numbers |
| `AA 81 00` | `AA 82 26 …` | Lifetime counters, see below | sensors |
| `AA 17 00` | `AA 16 01 00` | PartyBoost role (0 normal, 1 master, 2 slave) | — |
| `AA 4A 00` | `AA 4B 03 00 08 06` | DFU (OTA) version | — |
| `AA 4E 00` | `AA 4F 02 00 01` | Secondary firmware / stereo flag | — |
| `AA 33 00` | `AA 34 01 01` | MFB status (app never uses it on a Charge 5) | — |
| `AA 61 00` | `AA 62 01 00` | EQ mode (app never uses it on a Charge 5) | — |
| `AA A8 03 01 02 03` | **`AA EE`** | Player play/pause/skip/volume | **not supported** |
| `AA 9D 02 0C 0B` | `AA EE` | Usage summary | not supported |
| `AA 7A 00`, `77`, `68`, `71`, `56`, `B1`, `AB`, `98`, `A4`, `93`, `95`, `B4`, `B7`, `83`, `8B`, `8E` | `AA EE` | serial, bass vol, HFP, light, brightness, playtime boost, vendor codes, adv. EQ, LE audio, BR/EDR analytics, radio, screen, LEDs | not supported |

**Never send `AA 01 02 82 00`.** The app sends it right after reading
analytics and it wipes the speaker's lifetime counters.

### Token `0x44` battery — charging bit

`CommandProcessor` in the APK: a value `>= 0x80` means **charging**, level is
`value & 0x7F`. Before v0.3.0 the integration would have shown e.g. 208 % while
on the charger.

### Token `0x47` audio source

`0` none, `1` Bluetooth (A2DP), `2` AUX, `3` receiver, `4` FM, `5` DAB. Still
only "connected", not play/pause.

### Remaining tokens

`0x43` is the colour/model variant, `0x45` linked-device count (empty reply on a
Charge 5), `0x4A` is a CRC-16 of the MAC, `0xC2` secondary serial.

### Simple EQ (`0x6D`)

```
AA 6D 12 | 02 | 01 | 01 03 (01 00)(02 00)(03 00) | C1 03 (01 bb)(02 mm)(03 tt)
          scope active  Signature (flat)            Custom: bass / mid / treble
```

`scope = 2`, so each band is a signed byte in −2…+2. `active` is `01`
(JBL Signature) or `C1` (Custom). The speaker splits this 21-byte frame across
two notifications, so frames are reassembled by their length byte
(`protocol.reassemble`). Set custom: `AA 6E 08 C1 03 01 bb 02 mm 03 tt`; back
to Signature: `AA 6E 02 01 00`. Sending a `C1` entry with fewer bands than its
count byte stores garbage in the missing band.

### Analytics (`0x82`)

Big-endian u16 counters, Charge 5 order from
`ConnectingActivityViewModel.processDeviceAnalytics`: app connections, app
connected time, critical-temperature events, power-bank use, play time, play
time on battery, charging time, power-on count, power-on time, AUX play time,
USB-PD charging time, popular volume usage, popular volume level. The APK has no
units; power-on time grew by 8 over 8 minutes of a powered-on speaker, so the
integration treats durations as **minutes**.

### Advertising

Harman manufacturer data (company `0x0057`): `40 20 01 xx 00 00 <crc16 MAC>`,
i.e. PID `0x2040` little-endian, colour `01`, a status byte that changed between
`0x74` and `0xF4` across sessions (meaning unknown), and the MAC CRC.

### Media control

There is no transport or volume control for a Charge 5 over this protocol
(`0xA8` → `0xEE`), and the app has no AVRCP or MediaSession code. Play/pause,
skip and volume belong to whatever device streams A2DP to the speaker.
