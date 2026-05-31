# JBL Charge 5 — Home Assistant integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Read your **JBL Charge 5** battery level (and whether a source is connected) in
Home Assistant, over Bluetooth — no cloud, no app, no extra hardware.

The integration talks the speaker's native BLE GATT control protocol, which was
reverse-engineered and verified against real hardware. See
[`docs/PROTOCOL.md`](docs/PROTOCOL.md) for the full protocol and
[`docs/RECON_FINDINGS.md`](docs/RECON_FINDINGS.md) for how it was derived.

## Entities

| Entity | Type | Source |
|--------|------|--------|
| Battery | `sensor` (%, device_class battery) | protocol token `0x44` |
| In use | `binary_sensor` | protocol token `0x47` (a BT source is connected) |

The speaker is also registered as a device with its model, name, and MAC.

## Requirements

- Home Assistant 2024.6.0 or newer.
- A working Bluetooth adapter on the Home Assistant host (the
  [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/)
  set up and able to reach the speaker).
- The speaker powered on and in range. Pairing is not required — the control
  protocol runs over a separate BLE link.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/hudsonbrendon/jbl-charge5` as an **Integration**.
3. Install **JBL Charge 5**, then restart Home Assistant.
4. The speaker is auto-discovered via Bluetooth — confirm the prompt under
   **Settings → Devices & Services**. (Or add it manually with **+ Add
   Integration → JBL Charge 5**.)

### Manual

Copy `custom_components/jbl_charge5/` into your Home Assistant
`config/custom_components/` directory and restart.

## Known limitations

- **Play/pause is not exposed.** The control protocol reports whether a
  Bluetooth source is *connected* (`In use`), but not transport state — a
  paused-but-connected phone still reads "in use". True play/pause is AVRCP
  between the phone and the speaker and is outside this protocol.
- The integration polls on an interval (default 90s). If polling ever disturbs
  audio playback, increase the interval.

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]" -r requirements-test.txt
.venv/bin/pytest          # pure protocol tests + HA integration tests
```

The pure, reusable protocol codec lives in `src/jbl_charge5/` (and is vendored
into the integration). Recon scripts are under `scripts/`.
