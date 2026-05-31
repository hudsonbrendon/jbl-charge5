# JBL Charge 5 — Home Assistant Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a HACS-installable Home Assistant custom integration `jbl_charge5` that connects to a JBL Charge 5 over BLE and exposes its battery level (and a "source connected / in use" signal) as entities.

**Architecture:** Self-contained custom component at `custom_components/jbl_charge5/`. It vendors the recon-verified pure protocol codec (`protocol.py`, `tokens.py`) plus a new `parser.py` that turns the speaker's `0x12` notification burst into a `SpeakerInfo` dataclass. A `DataUpdateCoordinator` connects on an interval via `bleak-retry-connector.establish_connection` (using a `BLEDevice` obtained from HA's own Bluetooth stack — never a fresh `BleakScanner`), writes the `AA11` Speaker-Info request to characteristic `…0002`, collects the `0x12` replies on `…0001`, and parses them. A config flow auto-discovers the speaker by its custom service UUID.

**Tech Stack:** Python 3.12+ (HA runtime), Home Assistant 2024.6+ APIs (`entry.runtime_data`, typed `ConfigEntry`), `bleak-retry-connector`, `pytest-homeassistant-custom-component` for tests. No PyPI publish required — protocol code is vendored.

**Verified protocol facts (from recon — see `docs/PROTOCOL.md`):**
- Transport: BLE GATT. Service `65786365-6c70-6f69-6e74-2e636f6d0000`; write commands to `…0002` (write / write-without-response), responses notify on `…0001`.
- Request `AA 11` → burst of `0x12` frames, one token each, payload shape `00 <token> [len] <value…>`.
- Tokens: `0x44` battery % (1 byte), `0x47` audio-source state (0x00 idle / 0x01 BT source connected; NOT play/pause), `0x48` MAC (6 bytes), `0xC1` name (length-prefixed), `0x42` model (2 bytes), `0x43` color (1 byte), `0x46` channel (1 byte).
- Real frames captured: name `aa120f00c10c4a424c204368617267652035`, model `aa120400422040`, color `aa1203004301`, battery `aa1203004464` (=100%), channel `aa1203004600`, source `aa1203004701`, MAC `aa12080048aabbccddeeff`.

**Architecture note (DRY/vendoring trade-off):** `protocol.py` and `tokens.py` are copied verbatim from the recon library at `src/jbl_charge5/`. After Task 1 the copies under `custom_components/jbl_charge5/` are the canonical home for the integration; the `src/` versions remain frozen as recon artifacts. This avoids both a PyPI publish and a runtime path dependency, which HACS does not support. If the library is ever published to PyPI, replace the vendored files with a `requirements` entry.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `custom_components/jbl_charge5/__init__.py` | Entry setup/unload; build coordinator; forward platforms. |
| `custom_components/jbl_charge5/const.py` | Domain, scan interval, GATT UUIDs. |
| `custom_components/jbl_charge5/protocol.py` | **Vendored** pure frame codec (from recon). |
| `custom_components/jbl_charge5/tokens.py` | **Vendored** pure battery scan (from recon). |
| `custom_components/jbl_charge5/parser.py` | `SpeakerInfo` dataclass + `parse_speaker_info(frames)`. Pure. |
| `custom_components/jbl_charge5/bt.py` | `async_read_speaker_info(client)`: write request, collect notifications, parse. The BLE-I/O boundary. |
| `custom_components/jbl_charge5/coordinator.py` | `JblCharge5Coordinator(DataUpdateCoordinator[SpeakerInfo])`: connect + poll. |
| `custom_components/jbl_charge5/config_flow.py` | Bluetooth discovery + user pick flow. |
| `custom_components/jbl_charge5/entity.py` | `JblCharge5Entity` base (device info, CoordinatorEntity). |
| `custom_components/jbl_charge5/sensor.py` | Battery % sensor. |
| `custom_components/jbl_charge5/binary_sensor.py` | "In use" (source connected) binary sensor. |
| `custom_components/jbl_charge5/manifest.json` | Integration manifest (bluetooth matcher, deps, requirements). |
| `custom_components/jbl_charge5/strings.json` + `translations/en.json` | UI strings. |
| `hacs.json` | HACS metadata. |
| `tests/ha/conftest.py` | Enable custom integrations; common fixtures. |
| `tests/ha/test_parser.py` | TDD for parser (real frame fixtures). |
| `tests/ha/test_config_flow.py` | TDD for config flow. |
| `tests/ha/test_sensor.py` | TDD for coordinator → battery sensor + binary sensor. |
| `requirements-test.txt` | `pytest-homeassistant-custom-component`. |

---

## Task 1: Scaffold the integration directory + vendor protocol code

**Files:**
- Create: `custom_components/jbl_charge5/__init__.py` (temporary minimal — replaced in Task 7)
- Create: `custom_components/jbl_charge5/const.py`
- Create: `custom_components/jbl_charge5/protocol.py`
- Create: `custom_components/jbl_charge5/tokens.py`

- [ ] **Step 1: Vendor the codec**

Run (copies the recon-tested pure modules into the integration):
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
mkdir -p custom_components/jbl_charge5
cp src/jbl_charge5/protocol.py custom_components/jbl_charge5/protocol.py
cp src/jbl_charge5/tokens.py custom_components/jbl_charge5/tokens.py
```
Then edit `custom_components/jbl_charge5/tokens.py`: change the import line `from jbl_charge5.protocol import Token` to a package-relative import:
```python
from .protocol import Token
```
Expected: `custom_components/jbl_charge5/protocol.py` and `tokens.py` exist; `tokens.py` uses `from .protocol import Token`.

- [ ] **Step 2: Write `const.py`**

Create `custom_components/jbl_charge5/const.py`:
```python
"""Constants for the JBL Charge 5 integration."""

DOMAIN = "jbl_charge5"

# Poll interval (seconds). The speaker answers a Speaker-Info request quickly;
# polling every 90s keeps battery fresh without hammering the BLE link.
SCAN_INTERVAL_SECONDS = 90

# Custom GATT service/characteristics (verified on real hardware).
SERVICE_UUID = "65786365-6c70-6f69-6e74-2e636f6d0000"
WRITE_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"
NOTIFY_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0001"
```

- [ ] **Step 3: Write a temporary minimal `__init__.py`**

Create `custom_components/jbl_charge5/__init__.py`:
```python
"""The JBL Charge 5 integration."""
```
(The real setup logic is added in Task 7; this placeholder keeps the package importable for earlier tasks.)

- [ ] **Step 4: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add custom_components/jbl_charge5/
git commit -m "feat(ha): scaffold integration; vendor verified codec"
```

---

## Task 2: Test harness for HA tests

**Files:**
- Create: `requirements-test.txt`
- Create: `tests/ha/__init__.py`
- Create: `tests/ha/conftest.py`

- [ ] **Step 1: Write `requirements-test.txt`**

Create `/Users/hudsonbrendon/Github/jbl-charge5/requirements-test.txt`:
```text
pytest-homeassistant-custom-component
```

- [ ] **Step 2: Install it into the venv**

Run:
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
.venv/bin/pip install -r requirements-test.txt
```
Expected: installs `pytest-homeassistant-custom-component`, `homeassistant`, and pinned deps. (If `pip` is blocked by the sandbox, run in a plain terminal; report as DONE_WITH_CONCERNS if so.)

- [ ] **Step 3: Write the conftest**

Create `/Users/hudsonbrendon/Github/jbl-charge5/tests/ha/__init__.py` (empty file) and `/Users/hudsonbrendon/Github/jbl-charge5/tests/ha/conftest.py`:
```python
"""Fixtures for JBL Charge 5 HA tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield
```

- [ ] **Step 4: Add pytest path for the HA tests**

Edit `/Users/hudsonbrendon/Github/jbl-charge5/pyproject.toml`: replace the `[tool.pytest.ini_options]` block with:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["src", "."]
```
(Adding `"."` lets the test suite import `custom_components.jbl_charge5`.)

- [ ] **Step 5: Verify the recon tests still pass with the new path**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/test_protocol.py tests/test_tokens.py -q`
Expected: PASS (12 passed) — confirms the path change did not break the recon suite.

- [ ] **Step 6: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add requirements-test.txt tests/ha/__init__.py tests/ha/conftest.py pyproject.toml
git commit -m "test(ha): add pytest-homeassistant-custom-component harness"
```

---

## Task 3: `SpeakerInfo` parser (TDD)

**Files:**
- Create: `custom_components/jbl_charge5/parser.py`
- Create: `tests/ha/test_parser.py`

- [ ] **Step 1: Write the failing test**

Create `/Users/hudsonbrendon/Github/jbl-charge5/tests/ha/test_parser.py`:
```python
from custom_components.jbl_charge5.protocol import decode_frame
from custom_components.jbl_charge5.parser import SpeakerInfo, parse_speaker_info

# Real burst captured from a JBL Charge 5 on 2026-05-31 (battery was 100%).
REAL_FRAMES_HEX = [
    "aa120f00c10c4a424c204368617267652035",  # name "JBL Charge 5"
    "aa120400422040",                          # model 0x2040
    "aa1203004301",                            # color 0x01
    "aa1203004464",                            # battery 0x64 = 100
    "aa1203004600",                            # channel 0x00
    "aa1203004701",                            # source state 0x01 (connected)
    "aa12080048aabbccddeeff",                  # MAC aa:bb:cc:dd:ee:ff
]


def _frames():
    return [decode_frame(bytes.fromhex(h)) for h in REAL_FRAMES_HEX]


def test_parse_real_burst():
    info = parse_speaker_info(_frames())
    assert isinstance(info, SpeakerInfo)
    assert info.battery == 100
    assert info.source_connected is True
    assert info.name == "JBL Charge 5"
    assert info.model == 0x2040
    assert info.color == 0x01
    assert info.channel == 0x00
    assert info.mac == "aa:bb:cc:dd:ee:ff"


def test_parse_idle_source():
    # source token 0x00 -> not connected
    frames = [decode_frame(bytes.fromhex("aa1203004700"))]
    info = parse_speaker_info(frames)
    assert info.source_connected is False
    assert info.battery is None  # battery token absent in this partial burst


def test_parse_ignores_non_speaker_info_frames():
    frames = [decode_frame(bytes.fromhex("aa31"))]  # play-sound, not 0x12
    info = parse_speaker_info(frames)
    assert info.battery is None
    assert info.name is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/ha/test_parser.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.jbl_charge5.parser'`

- [ ] **Step 3: Write the implementation**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/parser.py`:
```python
"""Turn a burst of Speaker-Info (0x12) frames into a SpeakerInfo.

Each 0x12 payload is `00 <token> [len] <value...>`. Most tokens carry a
fixed-size value; 0xC1 (name) is length-prefixed; 0x48 (MAC) is 6 raw bytes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .protocol import Frame, PacketType, Token


@dataclass
class SpeakerInfo:
    battery: int | None = None
    source_connected: bool | None = None
    name: str | None = None
    model: int | None = None
    color: int | None = None
    channel: int | None = None
    mac: str | None = None
    raw: dict[int, str] = field(default_factory=dict)


def _token_value(payload: bytes) -> tuple[int, bytes] | None:
    """Payload is `00 <token> [len] <value>`. Return (token, value) or None."""
    if len(payload) < 3 or payload[0] != 0x00:
        return None
    token = payload[1]
    if token == Token.DEVICE_NAME:
        # length-prefixed: 00 C1 <len> <bytes>
        length = payload[2]
        return token, payload[3 : 3 + length]
    return token, payload[2:]


def parse_speaker_info(frames: list[Frame]) -> SpeakerInfo:
    info = SpeakerInfo()
    for frame in frames:
        if frame.packet_type != PacketType.SPEAKER_INFO_RESPONSE:
            continue
        parsed = _token_value(frame.payload)
        if parsed is None:
            continue
        token, value = parsed
        info.raw[token] = value.hex()
        if not value:
            continue
        if token == Token.BATTERY:
            info.battery = value[0]
        elif token == Token.AUDIO_SOURCE:
            info.source_connected = value[0] == 0x01
        elif token == Token.DEVICE_NAME:
            info.name = value.decode("ascii", errors="replace")
        elif token == Token.MODEL:
            info.model = int.from_bytes(value, "big")
        elif token == Token.COLOR:
            info.color = value[0]
        elif token == Token.AUDIO_CHANNEL:
            info.channel = value[0]
        elif token == Token.MAC:
            info.mac = ":".join(f"{b:02x}" for b in value)
    return info
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/ha/test_parser.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add custom_components/jbl_charge5/parser.py tests/ha/test_parser.py
git commit -m "feat(ha): SpeakerInfo parser for 0x12 token burst"
```

---

## Task 4: BLE read over a connected client

**Files:**
- Create: `custom_components/jbl_charge5/bt.py`
- Create: `tests/ha/test_bt.py`

- [ ] **Step 1: Write the failing test (with a fake client)**

Create `/Users/hudsonbrendon/Github/jbl-charge5/tests/ha/test_bt.py`:
```python
import asyncio

import pytest

from custom_components.jbl_charge5.bt import async_read_speaker_info
from custom_components.jbl_charge5 import const

REAL_FRAMES_HEX = [
    "aa1203004464",          # battery 100
    "aa1203004701",          # source connected
    "aa12080048aabbccddeeff",  # MAC
]


class FakeClient:
    """Minimal stand-in for a connected BleakClient."""

    def __init__(self):
        self._cb = None
        self.written = []

    async def start_notify(self, char, callback):
        self._cb = callback

    async def stop_notify(self, char):
        self._cb = None

    async def write_gatt_char(self, char, data, response=False):
        self.written.append((char, bytes(data), response))
        # Simulate the speaker answering with its burst.
        for h in REAL_FRAMES_HEX:
            self._cb(0, bytearray.fromhex(h))


@pytest.mark.asyncio
async def test_async_read_speaker_info(monkeypatch):
    # Make the collection window instant for the test.
    async def _instant(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _instant)

    client = FakeClient()
    info = await async_read_speaker_info(client)

    assert info.battery == 100
    assert info.source_connected is True
    assert info.mac == "aa:bb:cc:dd:ee:ff"
    # The request written must be the AA11 Speaker-Info request to the write char.
    char, data, response = client.written[0]
    assert char == const.WRITE_CHAR_UUID
    assert data == bytes([0xAA, 0x11])
    assert response is False
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/ha/test_bt.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.jbl_charge5.bt'`

- [ ] **Step 3: Write the implementation**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/bt.py`:
```python
"""BLE I/O boundary: ask a connected Charge 5 for its Speaker-Info."""

from __future__ import annotations

import asyncio

from .const import NOTIFY_CHAR_UUID, WRITE_CHAR_UUID
from .parser import SpeakerInfo, parse_speaker_info
from .protocol import PacketType, decode_frame, encode_frame

# The speaker answers the AA11 request with a quick burst; this is how long we
# listen for notifications before parsing what arrived.
COLLECT_SECONDS = 2.0


async def async_read_speaker_info(client, collect_seconds: float = COLLECT_SECONDS) -> SpeakerInfo:
    """Write the Speaker-Info request and parse the resulting 0x12 burst.

    `client` is an already-connected BleakClient-like object.
    """
    frames = []

    def on_notify(_handle, data: bytearray) -> None:
        try:
            frame = decode_frame(bytes(data))
        except ValueError:
            return
        if frame.packet_type == PacketType.SPEAKER_INFO_RESPONSE:
            frames.append(frame)

    await client.start_notify(NOTIFY_CHAR_UUID, on_notify)
    try:
        await client.write_gatt_char(
            WRITE_CHAR_UUID, encode_frame(PacketType.SPEAKER_INFO_REQUEST), response=False
        )
        await asyncio.sleep(collect_seconds)
    finally:
        await client.stop_notify(NOTIFY_CHAR_UUID)

    return parse_speaker_info(frames)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/ha/test_bt.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add custom_components/jbl_charge5/bt.py tests/ha/test_bt.py
git commit -m "feat(ha): async Speaker-Info read over a connected client"
```

---

## Task 5: Data update coordinator

**Files:**
- Create: `custom_components/jbl_charge5/coordinator.py`

- [ ] **Step 1: Write the coordinator**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/coordinator.py`:
```python
"""Coordinator that connects to the Charge 5 and polls Speaker-Info."""

from __future__ import annotations

import logging
from datetime import timedelta

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .bt import async_read_speaker_info
from .const import DOMAIN, SCAN_INTERVAL_SECONDS
from .parser import SpeakerInfo

_LOGGER = logging.getLogger(__name__)


class JblCharge5Coordinator(DataUpdateCoordinator[SpeakerInfo]):
    """Connect on an interval, read Speaker-Info, expose it to entities."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.address = address

    async def _async_update_data(self) -> SpeakerInfo:
        device = bluetooth.async_ble_device_from_address(self.hass, self.address, connectable=True)
        if device is None:
            raise UpdateFailed(f"JBL Charge 5 {self.address} not found / not in range")
        client = await establish_connection(
            BleakClientWithServiceCache, device, self.address
        )
        try:
            return await async_read_speaker_info(client)
        finally:
            await client.disconnect()
```

- [ ] **Step 2: Smoke-import to catch syntax/import errors**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/python -c "import custom_components.jbl_charge5.coordinator"`
Expected: no output, exit 0. (If `bleak_retry_connector` or `homeassistant` is missing, that means Task 2 Step 2 did not install the HA test deps — fix that first.)

- [ ] **Step 3: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add custom_components/jbl_charge5/coordinator.py
git commit -m "feat(ha): DataUpdateCoordinator connects and polls Speaker-Info"
```

---

## Task 6: Manifest + HACS metadata

**Files:**
- Create: `custom_components/jbl_charge5/manifest.json`
- Create: `hacs.json`

- [ ] **Step 1: Write the manifest**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/manifest.json`. Key order matters for hassfest: `domain` then `name` first, remaining keys alphabetically sorted.
```json
{
  "domain": "jbl_charge5",
  "name": "JBL Charge 5",
  "bluetooth": [
    { "service_uuid": "65786365-6c70-6f69-6e74-2e636f6d0000" },
    { "local_name": "JBL Charge 5*" }
  ],
  "codeowners": ["@hudsonbrendon"],
  "config_flow": true,
  "dependencies": ["bluetooth_adapters"],
  "documentation": "https://github.com/hudsonbrendon/jbl-charge5",
  "integration_type": "device",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/hudsonbrendon/jbl-charge5/issues",
  "requirements": ["bleak-retry-connector>=3.5.0"],
  "version": "0.1.0"
}
```

- [ ] **Step 2: Write `hacs.json`**

Create `/Users/hudsonbrendon/Github/jbl-charge5/hacs.json`:
```json
{
  "name": "JBL Charge 5",
  "render_readme": true,
  "homeassistant": "2024.6.0"
}
```

- [ ] **Step 3: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add custom_components/jbl_charge5/manifest.json hacs.json
git commit -m "feat(ha): manifest with bluetooth matcher + HACS metadata"
```

---

## Task 7: Entry setup, unload, and entity base

**Files:**
- Modify: `custom_components/jbl_charge5/__init__.py`
- Create: `custom_components/jbl_charge5/entity.py`

- [ ] **Step 1: Write the real `__init__.py`**

Replace `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/__init__.py` with:
```python
"""The JBL Charge 5 integration."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import JblCharge5Coordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

type JblConfigEntry = ConfigEntry[JblCharge5Coordinator]


async def async_setup_entry(hass: HomeAssistant, entry: JblConfigEntry) -> bool:
    """Set up JBL Charge 5 from a config entry."""
    address = entry.unique_id
    assert address is not None
    if bluetooth.async_ble_device_from_address(hass, address, connectable=True) is None:
        raise ConfigEntryNotReady(f"Could not find JBL Charge 5 with address {address}")

    coordinator = JblCharge5Coordinator(hass, address)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JblConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

- [ ] **Step 2: Write the entity base**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/entity.py`:
```python
"""Shared entity base for JBL Charge 5."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JblCharge5Coordinator


class JblCharge5Entity(CoordinatorEntity[JblCharge5Coordinator]):
    """Base entity with shared device info."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JblCharge5Coordinator) -> None:
        super().__init__(coordinator)
        address = coordinator.address
        info = coordinator.data
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            identifiers={(DOMAIN, address)},
            manufacturer="JBL",
            model=(info.name if info and info.name else "Charge 5"),
            name=(info.name if info and info.name else "JBL Charge 5"),
        )
```

- [ ] **Step 3: Smoke-import**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/python -c "import custom_components.jbl_charge5; import custom_components.jbl_charge5.entity"`
Expected: exit 0, no output.

- [ ] **Step 4: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add custom_components/jbl_charge5/__init__.py custom_components/jbl_charge5/entity.py
git commit -m "feat(ha): entry setup/unload + entity base"
```

---

## Task 8: Battery sensor + "in use" binary sensor

**Files:**
- Create: `custom_components/jbl_charge5/sensor.py`
- Create: `custom_components/jbl_charge5/binary_sensor.py`

- [ ] **Step 1: Write the battery sensor**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/sensor.py`:
```python
"""Battery sensor for the JBL Charge 5."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .entity import JblCharge5Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the battery sensor."""
    async_add_entities([JblBatterySensor(entry.runtime_data)])


class JblBatterySensor(JblCharge5Entity, SensorEntity):
    """Battery percentage reported by the speaker (token 0x44)."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_battery"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.battery
```

- [ ] **Step 2: Write the binary sensor**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/binary_sensor.py`:
```python
"""'In use' binary sensor for the JBL Charge 5 (source-connected, token 0x47)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .entity import JblCharge5Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the in-use binary sensor."""
    async_add_entities([JblInUseBinarySensor(entry.runtime_data)])


class JblInUseBinarySensor(JblCharge5Entity, BinarySensorEntity):
    """True when a Bluetooth audio source is connected (playing or paused)."""

    _attr_translation_key = "in_use"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_in_use"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.source_connected
```

- [ ] **Step 3: Smoke-import**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/python -c "import custom_components.jbl_charge5.sensor, custom_components.jbl_charge5.binary_sensor"`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add custom_components/jbl_charge5/sensor.py custom_components/jbl_charge5/binary_sensor.py
git commit -m "feat(ha): battery sensor + in-use binary sensor"
```

---

## Task 9: Config flow (TDD)

**Files:**
- Create: `custom_components/jbl_charge5/config_flow.py`
- Create: `custom_components/jbl_charge5/strings.json`
- Create: `custom_components/jbl_charge5/translations/en.json`
- Create: `tests/ha/test_config_flow.py`

- [ ] **Step 1: Write the failing test**

Create `/Users/hudsonbrendon/Github/jbl-charge5/tests/ha/test_config_flow.py`:
```python
from unittest.mock import patch

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import SOURCE_BLUETOOTH
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.jbl_charge5.const import DOMAIN, SERVICE_UUID

SERVICE_INFO = BluetoothServiceInfoBleak(
    name="JBL Charge 5",
    address="10:28:74:A4:8D:E7",
    rssi=-50,
    manufacturer_data={},
    service_data={},
    service_uuids=[SERVICE_UUID],
    source="local",
    device=None,
    advertisement=None,
    connectable=True,
    time=0,
    tx_power=-127,
)


async def test_bluetooth_discovery_flow(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=SERVICE_INFO
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    with patch(
        "custom_components.jbl_charge5.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "JBL Charge 5"
    assert result2["result"].unique_id == "10:28:74:A4:8D:E7"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/ha/test_config_flow.py -q`
Expected: FAIL — config flow not implemented (flow init errors / no `config_flow.py`).

- [ ] **Step 3: Write the config flow**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/config_flow.py`:
```python
"""Config flow for the JBL Charge 5 integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN

_NAME_MATCH = "charge 5"


class JblCharge5ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for JBL Charge 5."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a flow triggered by Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device."""
        assert self._discovery is not None
        if user_input is not None:
            return self.async_create_entry(title=self._discovery.name, data={})
        self._set_confirm_only()
        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"name": self._discovery.name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow started by the user (manual pick)."""
        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=self._discovered[address], data={})

        current = self._async_current_ids()
        for info in async_discovered_service_info(self.hass):
            if info.address in current:
                continue
            if info.name and _NAME_MATCH in info.name.lower():
                self._discovered[info.address] = info.name
        if not self._discovered:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("address"): vol.In(self._discovered)}),
        )
```

- [ ] **Step 4: Write `strings.json`**

Create `/Users/hudsonbrendon/Github/jbl-charge5/custom_components/jbl_charge5/strings.json`:
```json
{
  "config": {
    "flow_title": "{name}",
    "step": {
      "confirm": {
        "description": "Do you want to set up {name}?"
      },
      "user": {
        "data": {
          "address": "Device"
        }
      }
    },
    "abort": {
      "already_configured": "Device is already configured",
      "no_devices_found": "No JBL Charge 5 found nearby"
    }
  },
  "entity": {
    "binary_sensor": {
      "in_use": {
        "name": "In use"
      }
    }
  }
}
```

- [ ] **Step 5: Write `translations/en.json`**

Run:
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
mkdir -p custom_components/jbl_charge5/translations
cp custom_components/jbl_charge5/strings.json custom_components/jbl_charge5/translations/en.json
```
Expected: `translations/en.json` is an exact copy of `strings.json`.

- [ ] **Step 6: Run to verify pass**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/ha/test_config_flow.py -q`
Expected: PASS (1 passed)

- [ ] **Step 7: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add custom_components/jbl_charge5/config_flow.py custom_components/jbl_charge5/strings.json custom_components/jbl_charge5/translations/ tests/ha/test_config_flow.py
git commit -m "feat(ha): bluetooth discovery + manual config flow"
```

---

## Task 10: Sensor/coordinator integration test (TDD)

**Files:**
- Create: `tests/ha/test_sensor.py`

- [ ] **Step 1: Write the test**

Create `/Users/hudsonbrendon/Github/jbl-charge5/tests/ha/test_sensor.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jbl_charge5.const import DOMAIN
from custom_components.jbl_charge5.parser import SpeakerInfo

ADDRESS = "10:28:74:A4:8D:E7"


async def _setup(hass: HomeAssistant, info: SpeakerInfo):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="JBL Charge 5")
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.jbl_charge5.bluetooth.async_ble_device_from_address",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.jbl_charge5.coordinator.establish_connection",
            new=AsyncMock(return_value=AsyncMock()),
        ),
        patch(
            "custom_components.jbl_charge5.coordinator.async_read_speaker_info",
            new=AsyncMock(return_value=info),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_battery_and_in_use_entities(hass: HomeAssistant):
    info = SpeakerInfo(battery=100, source_connected=True, name="JBL Charge 5")
    entry = await _setup(hass, info)

    assert entry.state is ConfigEntryState.LOADED

    battery = hass.states.get("sensor.jbl_charge_5_battery")
    assert battery is not None
    assert battery.state == "100"

    in_use = hass.states.get("binary_sensor.jbl_charge_5_in_use")
    assert in_use is not None
    assert in_use.state == "on"
```

- [ ] **Step 2: Run the test**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/ha/test_sensor.py -q`
Expected: PASS (1 passed).

If the entity IDs differ (HA slugifies the device + entity name), read the failure's available `hass.states` to find the real IDs and update the assertions to match — the device name comes from `SpeakerInfo.name` ("JBL Charge 5") and the entity names are "Battery" / "In use".

- [ ] **Step 3: Run the full HA suite**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/ha -q`
Expected: PASS (all HA tests: parser, bt, config_flow, sensor).

- [ ] **Step 4: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add tests/ha/test_sensor.py
git commit -m "test(ha): coordinator -> battery sensor + in-use entity"
```

---

## Task 11: Validate with hassfest + final docs

**Files:**
- Create: `README.md` (or update if present)

- [ ] **Step 1: Run hassfest validation via the official Docker action locally**

Run (requires Docker; if unavailable, skip and note it):
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
docker run --rm -v "$PWD":/github/workspace ghcr.io/home-assistant/hassfest:latest || echo "hassfest skipped (no Docker)"
```
Expected: hassfest reports the `jbl_charge5` integration as valid (manifest keys in correct order, bluetooth matcher valid). Fix any reported manifest issues.

- [ ] **Step 2: Write the README**

Create/replace `/Users/hudsonbrendon/Github/jbl-charge5/README.md` with: what it is (HACS integration for JBL Charge 5 battery over BLE), install via HACS (custom repository), the entities provided (battery %, "in use"), the verified-protocol note linking `docs/PROTOCOL.md`, and the known limitation that play/pause is not exposed. Include a HACS badge and the manual-install path (`custom_components/jbl_charge5`).

- [ ] **Step 3: Set the GitHub repo description and topics** (HACS requirements)

Run (requires `gh` authenticated):
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
gh repo edit --description "Home Assistant integration for the JBL Charge 5 (battery over BLE)" \
  --add-topic home-assistant --add-topic hacs --add-topic jbl --add-topic bluetooth --add-topic ble \
  || echo "gh not configured — set description + topics in the GitHub UI"
```
Expected: repo has a description and topics (HACS validation requires both).

- [ ] **Step 4: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add README.md
git commit -m "docs: HACS install + entity docs for jbl_charge5"
```

- [ ] **Step 5: Stop and report**

Report: integration complete and tests green. Real-hardware verification (install in the user's Home Assistant 99lab, confirm the battery entity populates) is a manual step for the user, since it needs the running HA instance and the speaker.

---

## Self-Review

**Spec coverage:**
- Battery entity → Tasks 3 (parse), 4 (read), 5 (poll), 8 (sensor), 10 (verify). ✅
- "In use" (token 0x47) → Tasks 3, 8 (binary sensor), 10. ✅
- BLE-native connection via HA's stack → Task 5 (`async_ble_device_from_address` + `establish_connection`). ✅
- Auto-discovery → Task 6 (manifest bluetooth matcher), Task 9 (config flow). ✅
- HACS-installable → Tasks 6 (hacs.json), 11 (repo topics, README, hassfest). ✅
- Reuse verified protocol → Task 1 (vendored codec), Task 3 (parser from real frames). ✅

**Placeholder scan:** No "TODO/handle later". Task 11 Steps 1 and 3 depend on optional external tooling (Docker, `gh`); both have explicit fallbacks ("skip and note" / "set in UI"), so they are not blocking placeholders. Task 1's `__init__.py` is intentionally a stub, explicitly replaced with full code in Task 7.

**Type consistency:** `SpeakerInfo` (Task 3) fields — `battery`, `source_connected`, `name`, `model`, `color`, `channel`, `mac` — are the exact attributes read by `bt.py` (Task 4), `coordinator` data type (Task 5), `entity.py` device info (Task 7), `sensor.py` (`coordinator.data.battery`) and `binary_sensor.py` (`coordinator.data.source_connected`) (Task 8), and the tests (Tasks 3, 4, 10). `JblConfigEntry` / `entry.runtime_data` defined in Task 7 are consumed by both platforms in Task 8. UUID/interval constants live only in `const.py` (Task 1) and are imported everywhere — single source of truth. `JblCharge5Coordinator.address` set in Task 5 is read in Tasks 7 and 8.

**Risk notes (verify during execution, not blocking):**
- HA APIs evolve; `entry.runtime_data` + `type JblConfigEntry` require HA ≥ 2024.6. If the target HA is older, fall back to `hass.data[DOMAIN][entry.entry_id]`.
- Entity-id slugs in Task 10 assertions may need adjusting to HA's actual slugification (the step says how).
- Confirm the speaker tolerates HA's periodic BLE connect while streaming A2DP from a phone (the open coexistence question from recon). If polling drops audio, increase `SCAN_INTERVAL_SECONDS` or switch to an `ActiveBluetoothDataUpdateCoordinator` that only polls when the device is already advertising/connectable.
```
