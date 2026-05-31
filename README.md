<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/jbl_charge5/brand/dark_logo.png">
    <img src="custom_components/jbl_charge5/brand/logo.png" alt="JBL Charge 5" width="420">
  </picture>
</p>

# JBL Charge 5 for Home Assistant

[![Tests](https://github.com/hudsonbrendon/jbl-charge5/actions/workflows/tests.yml/badge.svg)](https://github.com/hudsonbrendon/jbl-charge5/actions/workflows/tests.yml)
[![Hassfest](https://github.com/hudsonbrendon/jbl-charge5/actions/workflows/hassfest.yml/badge.svg)](https://github.com/hudsonbrendon/jbl-charge5/actions/workflows/hassfest.yml)
[![Validate](https://github.com/hudsonbrendon/jbl-charge5/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/jbl-charge5/actions/workflows/validate.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/jbl-charge5)](https://github.com/hudsonbrendon/jbl-charge5/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Monitor and control a **JBL Charge 5** from Home Assistant over Bluetooth Low
Energy. See the battery level, know when something is playing through it, make
it beep to find it, toggle its feedback tones, and set its PartyBoost stereo
channel — all from the dashboard.

> Talks to the speaker's native BLE GATT control protocol, reverse-engineered
> and verified against real hardware. Everything runs on your LAN — no cloud, no
> account. Not affiliated with JBL or Harman.

## Features

- 🔋 **Battery level** — exact percentage reported by the speaker (token `0x44`).
- ▶️ **In use** — on when a Bluetooth audio source is connected (token `0x47`).
- 🔔 **Play sound** — button that makes the speaker emit its tone, to find it.
- 🔀 **Audio channel** — select Mono / Left / Right for PartyBoost stereo pairs.
- 🎚️ **Feedback tones** — switch to enable/disable the speaker's beeps.
- 🏷️ **Diagnostics** — model and Bluetooth MAC exposed as diagnostic sensors.
- 📡 **Local & private** — direct BLE, no cloud and no JBL app.

## Requirements

**On the speaker:**

- A JBL Charge 5, powered on and in Bluetooth range. Pairing is not required —
  the control protocol runs over its own BLE link.

**On Home Assistant:**

- Home Assistant **2024.6.0** or newer with the
  [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/)
  configured.
- A **connectable** Bluetooth path to the speaker. The Charge 5 is a dual-mode
  device whose control service lives on a BLE link that a host adapter often
  resolves onto its Classic identity instead — so an **ESP32 ESPHome Bluetooth
  Proxy with active connections** placed near the speaker is the reliable setup.
  See [Bluetooth proxy (required)](#bluetooth-proxy-required) below.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hudsonbrendon&repository=jbl-charge5&category=integration)

1. In Home Assistant, open **HACS → ⋮ (top right) → Custom repositories**.
2. Add `https://github.com/hudsonbrendon/jbl-charge5` and choose the
   **Integration** category — or use the button above.
3. Search for **JBL Charge 5** in HACS, install it, and **restart Home
   Assistant**.

### Manual

1. Copy `custom_components/jbl_charge5/` into your `config/custom_components/`.
2. Restart Home Assistant.

## Setup

1. Make sure the [Bluetooth proxy](#bluetooth-proxy-required) is online and near
   the speaker, and the speaker is powered on.
2. Home Assistant auto-discovers the speaker — confirm the prompt under
   **Settings → Devices & Services**. (Or add it with **+ Add Integration → JBL
   Charge 5** and pick it from the list.)

## Bluetooth proxy (required)

The Charge 5 exposes its control GATT service over **BLE only**, but it is also
a Classic (BR/EDR) audio device. A normal Home Assistant host adapter tends to
connect over Classic and never finds the control characteristics, or cannot
reach the right BLE address at all. The fix that works reliably is a dedicated
**ESPHome Bluetooth Proxy with active connections**, placed near the speaker —
ESP32 radios are LE-only, so they connect to the control service cleanly.

**Easiest — web flasher (no add-on needed):**

1. Plug an ESP32 into any computer and open
   <https://esphome.io/projects/?type=bluetooth-proxy> in Chrome or Edge.
2. Click **Connect**, pick the ESP32's serial port, and **Install Bluetooth
   Proxy** (this ready-made image already enables active connections).
3. Enter your Wi-Fi when prompted. Home Assistant discovers the proxy
   automatically.

**Or via the ESPHome add-on** — create a device and ensure its YAML contains:

```yaml
esp32_ble_tracker:
  scan_parameters:
    interval: 1100ms
    window: 1100ms
    active: true

bluetooth_proxy:
  active: true   # active connections are what lets HA reach the speaker
```

Place the proxy in the same room as the speaker. Once it is online, set up (or
reload) the JBL Charge 5 integration and the battery sensor populates.

## Entities

### Sensor

| Entity | Description |
|--------|-------------|
| `sensor.<name>_battery` | Battery level (%) |
| `sensor.<name>_model` | Model identifier (diagnostic) |
| `sensor.<name>_mac` | Bluetooth MAC address (diagnostic) |

### Binary sensor

| Entity | Description |
|--------|-------------|
| `binary_sensor.<name>_in_use` | On when a Bluetooth audio source is connected |

### Button

| Entity | Description |
|--------|-------------|
| `button.<name>_play_sound` | Make the speaker emit a tone (find it) |

### Switch

| Entity | Description |
|--------|-------------|
| `switch.<name>_feedback_tones` | Enable/disable the speaker's feedback tones |

### Select

| Entity | Description |
|--------|-------------|
| `select.<name>_audio_channel` | PartyBoost stereo channel: Mono / Left / Right |

## How it works

**The library.** `src/jbl_charge5/` is a pure, dependency-light Python codec for
the JBL/Harman `0xAA`-framed control protocol — framing (`protocol.py`), token
parsing (`tokens.py`/`parser.py`) and a `bleak` client. It is fully unit-tested
and is vendored into the integration so HACS needs no extra PyPI package. The
verified protocol is documented in [`docs/PROTOCOL.md`](docs/PROTOCOL.md), and
how it was reverse-engineered in
[`docs/RECON_FINDINGS.md`](docs/RECON_FINDINGS.md).

**The integration.** `custom_components/jbl_charge5/` adds a config flow
(Bluetooth discovery), a `DataUpdateCoordinator` that connects via
`bleak-retry-connector` and polls the speaker's Speaker-Info every 90 s, and the
entities above. To read state it writes a Speaker-Info request (`AA 11`) to the
write characteristic and parses the burst of token frames that come back on the
notify characteristic; control commands use the same write path.

**The ESP32 proxy.** Because the speaker's control service is only reachable
over LE, an ESPHome Bluetooth Proxy with active connections bridges Home
Assistant to it — see [Bluetooth proxy (required)](#bluetooth-proxy-required).

## Notes & limitations

- ⏯️ **Play/pause is not exposed.** `In use` reflects whether a source is
  *connected* (playing or paused both read on); true transport state is AVRCP,
  outside this protocol.
- 🎚️ **Feedback-tones switch is optimistic** — the protocol does not report its
  current state, so the switch assumes the last value you set.
- 📶 **Needs a connectable proxy near the speaker** (see above); a far-away host
  adapter may fail to connect.
- 🔌 Polling connects every 90 s; if it ever disturbs playback, raise the
  interval.

## Development

```bash
uv venv && uv pip install -r requirements_test.txt
.venv/bin/pytest        # pure codec tests + HA integration tests
.venv/bin/ruff check .
```

## License

[MIT](LICENSE)
