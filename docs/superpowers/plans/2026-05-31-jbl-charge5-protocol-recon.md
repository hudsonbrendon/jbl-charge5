# JBL Charge 5 Protocol Recon & RE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reverse-engineer the JBL Charge 5 control protocol and deliver a verified protocol spec plus a minimal Python proof-of-concept that reads battery level (and any status it exposes) from a real speaker — so the Home Assistant architecture can be chosen on facts, not guesses.

**Architecture:** The JBL "PartyBoost" generation (Charge 5) is hypothesized to expose Harman's control protocol over a **custom BLE GATT characteristic** (`UUID 65786365-6c70-6f69-6e74-2e636f6d0002`), based on the open-source `pembem22/connect-plus` Android app and its [protocol spec](https://github.com/pembem22/connect-plus/discussions/56). The protocol uses `0xAA`-framed packets. This recon project (1) confirms the transport (BLE GATT vs Classic RFCOMM/SPP), (2) verifies the packet framing and the battery token against a real Charge 5, and (3) wraps the findings in a tiny, fully-tested Python codec + PoC client. **No Home Assistant integration is built here** — that is a follow-up decided after this recon.

**Tech Stack:** Python 3.11+, [`bleak`](https://github.com/hbldh/bleak) (cross-platform BLE), `pytest`, `pytest-asyncio`. Recon tooling: macOS Bluetooth + `bleak` scanner; fallback capture via an Android phone (Developer Options → Bluetooth HCI snoop log) + Wireshark.

**Confidence legend used below:** ✅ confirmed from public source · ⚠️ hypothesis to verify against the real Charge 5 · ❓ open question.

### Protocol facts we are starting from (from `connect-plus`, NOT yet confirmed on Charge 5)

- ✅ Frame format: `0xAA | <packet_type> | <length> | <payload…>`. When there is **no payload**, the length byte is **omitted** (e.g. play-sound is just `AA 31`). When payload is present, length = number of payload bytes (e.g. `AA 67 01 01`, `AA 15 03 00 46 01`). No checksum.
- ✅ Packet types: `0x11` Speaker-Info-Request → `0x12` response; `0x41` Firmware-Version-Request → `0x42`; `0x31` Play-Sound; `0x15` Speaker-Info-Set.
- ✅ Response tokens (TLV inside payload): `0x42` model, `0x43` color, **`0x44` battery status**, `0x45` linked-device count, `0x46` audio channel, `0x47` audio source, `0x48` MAC, `0xC1` device name.
- ⚠️ Transport on Charge 5: BLE GATT characteristic `65786365-6c70-6f69-6e74-2e636f6d0002` (handle `0x000f` on the reference device). Older Connect+ models used Classic RFCOMM/SPP — Charge 5 transport MUST be confirmed (Task 2 / Task 5).
- ❓ "Is it playing?" — the spec exposes audio **source** (`0x47`), not play/pause state. Play/pause may only be observable via AVRCP and is treated as an open question, not a promised deliverable.

---

## File Structure

New git repository at `/Users/hudsonbrendon/Github/jbl-charge5`. Each file has one responsibility; the codec is pure/deterministic (easy to TDD) and isolated from all I/O.

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Project metadata + deps (`bleak`, `pytest`, `pytest-asyncio`). |
| `src/jbl_charge5/__init__.py` | Public exports. |
| `src/jbl_charge5/protocol.py` | **Pure** frame codec: `encode_frame`, `decode_frame`, `Frame`, packet-type/token constants. No I/O. |
| `src/jbl_charge5/tokens.py` | **Pure** TLV token parsing: `extract_battery`, `parse_speaker_info`. No I/O. |
| `src/jbl_charge5/client.py` | `bleak`-based async client: scan, connect, write request, await notification, return decoded info. The only file that touches Bluetooth. |
| `scripts/scan.py` | Recon CLI: scan for the Charge 5 and dump its GATT services/characteristics. |
| `scripts/poc_battery.py` | Recon CLI: connect and print battery + raw Speaker-Info response. |
| `tests/test_protocol.py` | TDD for `protocol.py` using real byte fixtures from the spec. |
| `tests/test_tokens.py` | TDD for `tokens.py`. |
| `docs/PROTOCOL.md` | **Primary deliverable:** the empirically-verified Charge 5 protocol, filled from real captures. |
| `docs/captures/` | Raw artifacts: `gatt_dump.txt`, `btsnoop_hci.log` (if Classic), annotated packet notes. |

---

## Task 0: Project skeleton & dependencies

**Files:**
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/pyproject.toml`
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/__init__.py`
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/.gitignore`

- [ ] **Step 1: Initialize the git repo**

Run:
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git init
```
Expected: `Initialized empty Git repository in /Users/hudsonbrendon/Github/jbl-charge5/.git/`

- [ ] **Step 2: Write `.gitignore`**

Create `/Users/hudsonbrendon/Github/jbl-charge5/.gitignore`:
```gitignore
__pycache__/
*.pyc
.venv/
.pytest_cache/
*.egg-info/
docs/captures/btsnoop_hci.log
```

- [ ] **Step 3: Write `pyproject.toml`**

Create `/Users/hudsonbrendon/Github/jbl-charge5/pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "jbl-charge5"
version = "0.0.1"
description = "Reverse-engineered control protocol + client for the JBL Charge 5"
requires-python = ">=3.11"
dependencies = ["bleak>=0.22"]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["src"]
```

- [ ] **Step 4: Write the package init**

Create `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/__init__.py`:
```python
"""Reverse-engineered JBL Charge 5 control protocol."""

__version__ = "0.0.1"
```

- [ ] **Step 5: Create venv and install**

Run:
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```
Expected: ends with `Successfully installed ... bleak ... pytest ...` (no errors).

- [ ] **Step 6: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add pyproject.toml .gitignore src/jbl_charge5/__init__.py
git commit -m "chore: project skeleton with bleak + pytest"
```

---

## Task 1: Frame codec — encode (TDD)

The encoder is pure and deterministic. We test it against the **real example bytes** documented in the `connect-plus` spec, so these tests are authoritative regardless of what the speaker turns out to do.

**Files:**
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/protocol.py`
- Test: `/Users/hudsonbrendon/Github/jbl-charge5/tests/test_protocol.py`

- [ ] **Step 1: Write the failing test**

Create `/Users/hudsonbrendon/Github/jbl-charge5/tests/test_protocol.py`:
```python
from jbl_charge5.protocol import encode_frame, PacketType


def test_encode_no_payload_omits_length_byte():
    # connect-plus spec: play-sound is just AA 31, no length byte.
    assert encode_frame(PacketType.PLAY_SOUND) == bytes([0xAA, 0x31])


def test_encode_with_payload_includes_length():
    # spec: enable feedback sounds = AA 67 01 01
    assert encode_frame(0x67, b"\x01") == bytes([0xAA, 0x67, 0x01, 0x01])


def test_encode_multibyte_payload_length():
    # spec: set left channel = AA 15 03 00 46 01
    assert encode_frame(0x15, bytes([0x00, 0x46, 0x01])) == bytes([0xAA, 0x15, 0x03, 0x00, 0x46, 0x01])


def test_speaker_info_request_is_aa11():
    # No payload => no length byte.
    assert encode_frame(PacketType.SPEAKER_INFO_REQUEST) == bytes([0xAA, 0x11])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/test_protocol.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'jbl_charge5.protocol'`

- [ ] **Step 3: Write minimal implementation**

Create `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/protocol.py`:
```python
"""Pure, I/O-free codec for the JBL/Harman 0xAA-framed control protocol.

Frame layout (from pembem22/connect-plus discussion #56):
    0xAA | packet_type | [length | payload...]
The length byte and payload are present only when there is a payload.
No checksum.
"""

from enum import IntEnum

PREAMBLE = 0xAA


class PacketType(IntEnum):
    ACK = 0x00
    SPEAKER_INFO_REQUEST = 0x11
    SPEAKER_INFO_RESPONSE = 0x12
    SPEAKER_INFO_SET = 0x15
    PLAY_SOUND = 0x31
    FIRMWARE_VERSION_REQUEST = 0x41
    FIRMWARE_VERSION_RESPONSE = 0x42


class Token(IntEnum):
    MODEL = 0x42
    COLOR = 0x43
    BATTERY = 0x44
    LINKED_DEVICES = 0x45
    AUDIO_CHANNEL = 0x46
    AUDIO_SOURCE = 0x47
    MAC = 0x48
    DEVICE_NAME = 0xC1


def encode_frame(packet_type: int, payload: bytes = b"") -> bytes:
    """Build a control frame. Length byte is omitted when payload is empty."""
    if not payload:
        return bytes([PREAMBLE, packet_type])
    if len(payload) > 0xFF:
        raise ValueError("payload too long for single-byte length field")
    return bytes([PREAMBLE, packet_type, len(payload)]) + payload
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/test_protocol.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add src/jbl_charge5/protocol.py tests/test_protocol.py
git commit -m "feat: frame encoder for JBL 0xAA control protocol"
```

---

## Task 2: Frame codec — decode (TDD)

**Files:**
- Modify: `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/protocol.py`
- Modify: `/Users/hudsonbrendon/Github/jbl-charge5/tests/test_protocol.py`

- [ ] **Step 1: Write the failing test (append to the test file)**

Append to `/Users/hudsonbrendon/Github/jbl-charge5/tests/test_protocol.py`:
```python
import pytest
from jbl_charge5.protocol import decode_frame, Frame


def test_decode_no_payload_frame():
    frame = decode_frame(bytes([0xAA, 0x31]))
    assert frame == Frame(packet_type=0x31, payload=b"")


def test_decode_frame_with_payload():
    frame = decode_frame(bytes([0xAA, 0x12, 0x02, 0x44, 0x4B]))
    assert frame == Frame(packet_type=0x12, payload=bytes([0x44, 0x4B]))


def test_decode_rejects_bad_preamble():
    with pytest.raises(ValueError, match="preamble"):
        decode_frame(bytes([0xBB, 0x12, 0x00]))


def test_decode_rejects_truncated_payload():
    # length says 5 but only 1 payload byte present
    with pytest.raises(ValueError, match="truncated"):
        decode_frame(bytes([0xAA, 0x12, 0x05, 0x44]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/test_protocol.py -k decode -v`
Expected: FAIL with `ImportError: cannot import name 'decode_frame'`

- [ ] **Step 3: Write minimal implementation (append to `protocol.py`)**

Append to `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/protocol.py`:
```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Frame:
    packet_type: int
    payload: bytes = field(default=b"")


def decode_frame(data: bytes) -> Frame:
    """Parse a single control frame. Raises ValueError on malformed input."""
    if len(data) < 2 or data[0] != PREAMBLE:
        raise ValueError(f"bad preamble or too short: {data.hex()}")
    packet_type = data[1]
    if len(data) == 2:
        return Frame(packet_type=packet_type, payload=b"")
    length = data[2]
    payload = data[3:]
    if len(payload) < length:
        raise ValueError(f"truncated payload: want {length}, got {len(payload)}")
    return Frame(packet_type=packet_type, payload=payload[:length])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/test_protocol.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add src/jbl_charge5/protocol.py tests/test_protocol.py
git commit -m "feat: frame decoder with malformed-input guards"
```

---

## Task 3: Token parsing — battery extraction (TDD)

The Speaker-Info response (`0x12`) payload is a sequence of TLV tokens. For recon we only need the battery token (`0x44`, followed by one byte = percentage). We keep this minimal (YAGNI) and deterministic.

**Files:**
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/tokens.py`
- Test: `/Users/hudsonbrendon/Github/jbl-charge5/tests/test_tokens.py`

- [ ] **Step 1: Write the failing test**

Create `/Users/hudsonbrendon/Github/jbl-charge5/tests/test_tokens.py`:
```python
from jbl_charge5.tokens import extract_battery


def test_extract_battery_basic():
    # token 0x44 followed by battery percentage 0x4B == 75
    assert extract_battery(bytes([0x44, 0x4B])) == 75


def test_extract_battery_when_surrounded_by_other_tokens():
    # model token (0x42, len-prefixed) then battery then linked-devices
    payload = bytes([0x42, 0x01, 0x07, 0x44, 0x32, 0x45, 0x01, 0x00])
    assert extract_battery(payload) == 50


def test_extract_battery_absent_returns_none():
    assert extract_battery(bytes([0x45, 0x01, 0x00])) is None
```

> Note: `test_extract_battery_when_surrounded_by_other_tokens` assumes model/linked tokens are length-prefixed. The exact TLV grammar for *other* tokens is ⚠️ unconfirmed — but `extract_battery` does not need to fully parse them; it scans for the `0x44` marker and reads the next byte. This test pins that scan behavior. Real-capture verification happens in Task 7.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/test_tokens.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'jbl_charge5.tokens'`

- [ ] **Step 3: Write minimal implementation**

Create `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/tokens.py`:
```python
"""Pure helpers to pull values out of a Speaker-Info (0x12) payload.

Token grammar is only partially confirmed. `extract_battery` deliberately
scans for the battery marker rather than fully parsing the TLV stream, so it
is robust to unknown neighbouring tokens. Verified against a real Charge 5
capture in the recon tasks.
"""

from jbl_charge5.protocol import Token


def extract_battery(payload: bytes) -> int | None:
    """Return battery percentage (0-100) or None if the token is absent."""
    i = 0
    while i < len(payload) - 1:
        if payload[i] == Token.BATTERY:
            return payload[i + 1]
        i += 1
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest tests/test_tokens.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add src/jbl_charge5/tokens.py tests/test_tokens.py
git commit -m "feat: battery token extraction from Speaker-Info payload"
```

---

## Task 4: BLE scan recon script — confirm the transport

This is investigative. Goal: prove whether the Charge 5 exposes the custom GATT characteristic over BLE. This decides the entire downstream architecture.

**Files:**
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/scripts/scan.py`

- [ ] **Step 1: Write the scan script**

Create `/Users/hudsonbrendon/Github/jbl-charge5/scripts/scan.py`:
```python
"""Recon: find the JBL Charge 5 over BLE and dump its GATT table.

Usage:
    .venv/bin/python scripts/scan.py            # list all BLE devices
    .venv/bin/python scripts/scan.py "JBL"      # connect to first match, dump GATT
"""

import asyncio
import sys

from bleak import BleakClient, BleakScanner

CONTROL_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"


async def main(name_filter: str | None) -> None:
    print("Scanning 10s for BLE devices...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        print(f"  {d.address}  rssi={getattr(d, 'rssi', '?')}  name={d.name!r}")

    if not name_filter:
        print("\nPass a name substring (e.g. 'JBL') to connect and dump GATT.")
        return

    match = next((d for d in devices if d.name and name_filter.lower() in d.name.lower()), None)
    if not match:
        print(f"\nNo device matching {name_filter!r}. Put the speaker in pairing mode and retry.")
        return

    print(f"\nConnecting to {match.name} ({match.address})...")
    async with BleakClient(match.address) as client:
        print("Connected. Services / characteristics:")
        found_control = False
        for service in client.services:
            print(f"  [service] {service.uuid}")
            for ch in service.characteristics:
                flags = ",".join(ch.properties)
                marker = "  <-- CONTROL CHARACTERISTIC" if ch.uuid.lower() == CONTROL_CHAR_UUID else ""
                print(f"    [char] {ch.uuid}  ({flags}){marker}")
                if ch.uuid.lower() == CONTROL_CHAR_UUID:
                    found_control = True
        print()
        if found_control:
            print(f"FOUND custom control characteristic {CONTROL_CHAR_UUID} -> BLE path is viable.")
        else:
            print("Custom control characteristic NOT found over BLE.")
            print("=> Charge 5 likely uses Classic RFCOMM/SPP. Proceed to Task 6 (btsnoop capture).")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
```

- [ ] **Step 2: Run the scan with the speaker powered on**

Run:
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
.venv/bin/python scripts/scan.py "JBL"
```
Expected (one of two outcomes — record which):
- **A:** Output ends with `FOUND custom control characteristic ... -> BLE path is viable.` → continue to Task 5.
- **B:** Output ends with `Custom control characteristic NOT found ... Proceed to Task 6` → skip Task 5, do Task 6, then resume at Task 7.

> macOS note: `bleak` reports an opaque CoreBluetooth UUID, not the speaker's MAC. That is fine for connecting. The MAC (token `0x48`) can still be read from the protocol later.

- [ ] **Step 3: Save the GATT dump as an artifact**

Run:
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
mkdir -p docs/captures
.venv/bin/python scripts/scan.py "JBL" | tee docs/captures/gatt_dump.txt
```
Expected: `docs/captures/gatt_dump.txt` exists and contains the service/characteristic listing.

- [ ] **Step 4: Commit the script and artifact**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add scripts/scan.py docs/captures/gatt_dump.txt
git commit -m "feat: BLE recon scan; record Charge 5 GATT table"
```

---

## Task 5: PoC client over BLE — read battery from the real speaker

**Do this task only if Task 4 outcome was A (control characteristic found over BLE).** If outcome was B, skip to Task 6.

**Files:**
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/client.py`
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/scripts/poc_battery.py`

- [ ] **Step 1: Write the BLE client**

Create `/Users/hudsonbrendon/Github/jbl-charge5/src/jbl_charge5/client.py`:
```python
"""Minimal async BLE client for the JBL Charge 5 control protocol.

Only file that performs Bluetooth I/O. Decoding is delegated to the pure
protocol/tokens modules.
"""

import asyncio

from bleak import BleakClient, BleakScanner

from jbl_charge5.protocol import PacketType, decode_frame, encode_frame
from jbl_charge5.tokens import extract_battery

CONTROL_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"


async def find_speaker(name_filter: str = "JBL") -> str:
    """Return the BLE address of the first matching speaker. Raises if none."""
    devices = await BleakScanner.discover(timeout=10.0)
    match = next((d for d in devices if d.name and name_filter.lower() in d.name.lower()), None)
    if not match:
        raise RuntimeError(f"No BLE device matching {name_filter!r}")
    return match.address


async def read_speaker_info(address: str, timeout: float = 5.0) -> dict:
    """Connect, request Speaker Info, return {'battery': int|None, 'raw': hex}."""
    response: asyncio.Future = asyncio.get_event_loop().create_future()

    def on_notify(_handle, data: bytearray) -> None:
        frame = decode_frame(bytes(data))
        if frame.packet_type == PacketType.SPEAKER_INFO_RESPONSE and not response.done():
            response.set_result(frame)

    async with BleakClient(address) as client:
        await client.start_notify(CONTROL_CHAR_UUID, on_notify)
        await client.write_gatt_char(
            CONTROL_CHAR_UUID,
            encode_frame(PacketType.SPEAKER_INFO_REQUEST),
            response=False,
        )
        frame = await asyncio.wait_for(response, timeout=timeout)
        await client.stop_notify(CONTROL_CHAR_UUID)

    return {"battery": extract_battery(frame.payload), "raw": frame.payload.hex()}
```

- [ ] **Step 2: Write the PoC runner**

Create `/Users/hudsonbrendon/Github/jbl-charge5/scripts/poc_battery.py`:
```python
"""Recon PoC: print the Charge 5 battery level and the raw Speaker-Info payload."""

import asyncio

from jbl_charge5.client import find_speaker, read_speaker_info


async def main() -> None:
    address = await find_speaker("JBL")
    print(f"Speaker at {address}")
    info = await read_speaker_info(address)
    print(f"Battery: {info['battery']}%")
    print(f"Raw Speaker-Info payload: {info['raw']}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Run against the real speaker**

Run:
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
.venv/bin/python scripts/poc_battery.py
```
Expected: prints a plausible battery percentage (cross-check against the JBL Portable app on your phone) and a raw hex payload. **Record the exact raw payload** — it becomes the real fixture in Task 7.

If it times out: the request packet shape (`AA 11` with no payload) may be wrong, or notifications come on a different characteristic. Inspect with `scripts/scan.py` output, try writing with `response=True`, and try subscribing to every notifiable characteristic. Note findings; this is expected recon iteration.

- [ ] **Step 4: Save the raw payload artifact**

Run:
```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
.venv/bin/python scripts/poc_battery.py | tee docs/captures/speaker_info_response.txt
```
Expected: file contains the battery line and raw payload hex.

- [ ] **Step 5: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add src/jbl_charge5/client.py scripts/poc_battery.py docs/captures/speaker_info_response.txt
git commit -m "feat: BLE PoC client reads Charge 5 battery via Speaker-Info"
```

---

## Task 6: Classic RFCOMM capture fallback

**Do this task only if Task 4 outcome was B (no BLE control characteristic).** This captures the protocol from the official JBL Portable app over Bluetooth Classic, using an Android phone. After decoding, you implement a Classic client instead of the BLE one. If Task 5 succeeded, skip this task entirely.

**Files:**
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/docs/captures/btsnoop_notes.md`

- [ ] **Step 1: Enable HCI snoop logging on Android**

On an Android phone with the **JBL Portable** app installed and the speaker paired:
1. Settings → About phone → tap "Build number" 7× to enable Developer options.
2. Settings → System → Developer options → enable **"Enable Bluetooth HCI snoop log"**.
3. Toggle Bluetooth off and on to start a fresh log.

Reference: [Gadgetbridge BT RE wiki](https://codeberg.org/Freeyourgadget/Gadgetbridge/wiki/BT-Protocol-Reverse-Engineering).

- [ ] **Step 2: Perform and label actions in the app**

Open the JBL Portable app, connect to the Charge 5, and do these actions, noting the wall-clock time of each (you will correlate them to packets):
- Open the app's home screen (this is where battery % shows).
- Trigger a "play sound"/feedback tone if available.
- Read the firmware version screen.

- [ ] **Step 3: Pull the snoop log**

Run (phone connected via USB with USB debugging on):
```bash
adb root
adb pull /data/misc/bluetooth/logs/btsnoop_hci.log /Users/hudsonbrendon/Github/jbl-charge5/docs/captures/btsnoop_hci.log
```
Expected: `btsnoop_hci.log` downloaded. If the path differs, run `adb shell cat /etc/bluetooth/bt_stack.conf | grep -i btsnoop` to find it. Non-rooted phones: use Wireshark's "Android Bluetooth Btsnoop" live interface instead.

- [ ] **Step 4: Decode in Wireshark**

1. Open `btsnoop_hci.log` in Wireshark.
2. Filter to the speaker's RFCOMM traffic: `btrfcomm`.
3. Find frames whose data starts with `aa` — the preamble. Identify the battery exchange: look for a request near your "home screen" timestamp and a response containing token `44` followed by a byte close to the app's displayed %.
4. Record into `docs/captures/btsnoop_notes.md`: the RFCOMM **channel number**, the exact request bytes for Speaker-Info, and the full response bytes (so the `0x44` battery position is confirmed).

- [ ] **Step 5: Write the notes file**

Create `/Users/hudsonbrendon/Github/jbl-charge5/docs/captures/btsnoop_notes.md` with the captured findings, for example:
```markdown
# Charge 5 Classic RFCOMM capture

- Transport: Bluetooth Classic RFCOMM, channel <N>
- Speaker-Info request bytes: aa 11 ...
- Speaker-Info response bytes: aa 12 <len> ... 44 <battery> ...
- Confirmed battery token 0x44 at payload offset <k>; app showed <X>%, byte was 0x<hh>.
```

- [ ] **Step 6: (If Classic) add a Classic client variant**

If Classic is the transport, the BLE `client.py` is replaced by a `socket(AF_BLUETOOTH, SOCK_STREAM, BTPROTO_RFCOMM)` client (Linux) or `pybluez`. This is a **non-trivial deviation** that affects the HA architecture decision — stop and report it before building further, then resume the architecture choice with the user. Document the RFCOMM channel in `docs/PROTOCOL.md`.

- [ ] **Step 7: Commit the capture notes**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add docs/captures/btsnoop_notes.md
git commit -m "docs: Classic RFCOMM capture notes for Charge 5"
```

---

## Task 7: Lock the verified protocol into a real fixture & deliverable doc

Turn the empirical capture into a regression test and the project's primary deliverable.

**Files:**
- Modify: `/Users/hudsonbrendon/Github/jbl-charge5/tests/test_tokens.py`
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/docs/PROTOCOL.md`

- [ ] **Step 1: Add a real-capture regression test**

Append to `/Users/hudsonbrendon/Github/jbl-charge5/tests/test_tokens.py`, replacing `<PASTE…>` with the real bytes recorded in Task 5 Step 4 (or Task 6 Step 4) and `<N>` with the battery % the app showed at capture time:
```python
from jbl_charge5.protocol import decode_frame, PacketType


def test_real_charge5_speaker_info_capture():
    # Captured from a real JBL Charge 5 on 2026-05-31 (app showed <N>%).
    raw_frame = bytes.fromhex("<PASTE FULL FRAME HEX e.g. aa12...>")
    frame = decode_frame(raw_frame)
    assert frame.packet_type == PacketType.SPEAKER_INFO_RESPONSE
    assert extract_battery(frame.payload) == <N>
```

- [ ] **Step 2: Run the full suite**

Run: `cd /Users/hudsonbrendon/Github/jbl-charge5 && .venv/bin/pytest -v`
Expected: PASS (all tests, including the new real-capture test). If the real-capture test fails, the codec/token logic does not match reality — fix `protocol.py`/`tokens.py` to match the captured bytes (the capture is ground truth), then re-run.

- [ ] **Step 3: Write the deliverable protocol doc**

Create `/Users/hudsonbrendon/Github/jbl-charge5/docs/PROTOCOL.md` documenting, from the verified capture: the confirmed transport (BLE GATT char UUID *or* Classic RFCOMM channel), the exact frame format, the Speaker-Info request/response bytes, the battery token position, and a clear list of what is still unknown (notably play/pause state). Include whether the speaker exposes the protocol while simultaneously streaming audio from a phone (test this and note it — it determines whether HA can poll without interrupting playback).

- [ ] **Step 4: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add tests/test_tokens.py docs/PROTOCOL.md
git commit -m "test: pin real Charge 5 capture; docs: verified protocol spec"
```

---

## Task 8: Recon report & architecture recommendation

**Files:**
- Create: `/Users/hudsonbrendon/Github/jbl-charge5/docs/RECON_FINDINGS.md`

- [ ] **Step 1: Write the findings summary**

Create `/Users/hudsonbrendon/Github/jbl-charge5/docs/RECON_FINDINGS.md` answering, with evidence from this project:
- Transport confirmed (BLE GATT vs Classic RFCOMM)?
- Battery readable? How reliably (does it need the speaker awake/connected)?
- Does reading interfere with audio playback?
- Is play/pause state obtainable at all?
- **Recommended HA architecture** given the above:
  - If **BLE GATT** → a native HA Bluetooth (`bleak`) custom component is viable; recommend that path.
  - If **Classic RFCOMM** → HA's BT stack can't reach it; recommend a sidecar (Raspberry Pi / ESP32) bridging via MQTT.

- [ ] **Step 2: Commit**

```bash
cd /Users/hudsonbrendon/Github/jbl-charge5
git add docs/RECON_FINDINGS.md
git commit -m "docs: recon findings and HA architecture recommendation"
```

- [ ] **Step 3: Stop and report**

Recon is complete. Present `docs/RECON_FINDINGS.md` to the user and decide the Home Assistant integration architecture in a follow-up plan. **Do not start the HA integration without that decision.**

---

## Self-Review

**Spec coverage (vs the user's original ask):**
- "nível de bateria" → Tasks 3, 5/6, 7 (token `0x44`, verified against real device). ✅
- "id do Bluetooth" → MAC token `0x48` surfaced by the scan (Task 4) and Speaker-Info payload; documented in PROTOCOL.md. ✅
- "se está tocando ou não" → Honestly flagged as ❓ open (audio *source* `0x47` exists; play/pause likely AVRCP-only). Tracked as an explicit unknown in Tasks 7–8, not over-promised. ✅
- "ou qualquer coisa do tipo" → model/color/firmware/linked-devices tokens enumerated in `protocol.py`. ✅
- "lib em Python para integração com Home Assistant / Custom Components" → This plan deliberately stops at the recon/RE phase the user selected; it produces the verified protocol + a tested codec + PoC that the HA component will reuse, and ends with an architecture recommendation. ✅ (scope-correct)

**Placeholder scan:** The only intentional `<PLACEHOLDER>` is the real-capture hex in Task 7 Step 1 — that is empirical data that *must* come from the live speaker, with an explicit capture mechanism (Task 5/6) and a verification step (Task 7 Step 2). All code in Tasks 0–5 is complete and runnable. No "TODO/handle edge cases/similar to" placeholders.

**Type consistency:** `encode_frame`/`decode_frame`/`Frame`/`PacketType`/`Token` defined in Task 1–2 are used consistently in Tasks 3 and 5. `extract_battery` (Task 3) is consumed unchanged by `client.py` (Task 5) and the regression test (Task 7). `CONTROL_CHAR_UUID` string is identical in `scan.py` and `client.py`.

**Known branch point:** Task 4 splits the plan (BLE vs Classic). Both branches converge at Task 7. This is inherent to recon — the transport is the central unknown being resolved.
