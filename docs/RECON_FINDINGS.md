# JBL Charge 5 → Home Assistant — Recon Findings

**Date:** 2026-05-31 · **Verdict: viable, BLE-native path confirmed.**

## Questions answered

| Question | Answer |
|----------|--------|
| Transport? | **BLE GATT** (custom service `…0000`; write `…0002`, notify/read `…0001`). No Classic/RFCOMM needed. |
| Battery readable? | **Yes** — token `0x44`, confirmed 100% live. Write `AA11` to `…0002`, read `0x12` notifications on `…0001`. |
| Bluetooth id? | **Yes** — MAC `aa:bb:cc:dd:ee:ff` (token `0x48`). |
| Other info? | Device name "JBL Charge 5", model `0x2040`, color, audio channel, audio source. |
| Source / in-use? | **Yes (proxy)** — token `0x47`: `0x00` idle, `0x01` BT source connected. |
| Play/pause state? | **Not exposed** — `0x47` stays `0x01` whether playing OR paused (verified). True play/pause is AVRCP between phone↔speaker, outside this protocol. For HA, use `0x47` as an "in use / source connected" binary_sensor; detect real play/pause at the source if needed. |
| Interferes with audio playback? | Not yet tested (does the BLE control link coexist with A2DP streaming from a phone). |

## Recommended HA architecture

**Native Home Assistant Bluetooth (`bleak`) custom integration.** Because control
is BLE GATT (not Classic RFCOMM), Home Assistant's own Bluetooth stack can reach
the speaker directly — no Raspberry Pi / ESP32 sidecar, no MQTT bridge required.

Reuse the modules built in this repo:
- `protocol.py` (frame codec), `tokens.py` (battery extraction) — pure, tested.
- `client.py` — `bleak` client; write request to `…0002`, parse notifications
  from `…0001`.

Integration shape (next plan):
- `sensor` battery % (token `0x44`); attributes for model/color/name/MAC.
- Device polled on an interval; HA's `bluetooth` integration provides the adapter.
- Consider a `binary_sensor`/state once play/pause is resolved.

### Caveats for the HA build
- Runs on the HA host's BLE adapter (Linux — no macOS TCC issue).
- Connection model: the speaker accepted a BLE control connection during recon;
  confirm it tolerates that while also playing A2DP audio, and that polling
  cadence does not drop the audio link.
- BLE address handling differs per OS (macOS gives an opaque UUID; Linux/HA gives
  the real MAC) — HA should match on the MAC `aa:bb:cc:dd:ee:ff` / name.

## Immediate optional follow-up (still recon)
- Differential capture for play/pause: play music, re-run `scripts/poc_battery.py`,
  diff the `0x47` token (and watch for any new token).

## How recon was run (reproducible)
- Pure codec/token logic: `.venv/bin/pytest` (12 tests, incl. real-capture fixture).
- Live BLE on macOS: copied Homebrew `Python.app` → added
  `NSBluetoothAlwaysUsageDescription` to its `Info.plist` → ad-hoc re-signed →
  launched via `open -W -a .bt/Python.app --args -u scripts/<script>.py`.
- Artifacts: `docs/captures/gatt_dump.txt`, `docs/captures/speaker_info_response.txt`.
