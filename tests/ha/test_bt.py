import asyncio

import pytest

from custom_components.jbl_charge5 import const
from custom_components.jbl_charge5.bt import async_read_speaker_info

REAL_FRAMES_HEX = [
    "aa1203004464",  # battery 100
    "aa1203004701",  # source connected
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


@pytest.mark.asyncio
async def test_send_command_serializes_and_waits_for_ack(monkeypatch):
    """Overlapping commands queue on one BLE link and write with response."""
    import bleak_retry_connector
    from homeassistant.components import bluetooth

    from custom_components.jbl_charge5.bt import async_send_command

    open_links, max_open, writes = 0, 0, []

    class Link:
        async def write_gatt_char(self, char, data, response=False):
            writes.append(response)
            await asyncio.sleep(0.01)

        async def disconnect(self):
            nonlocal open_links
            open_links -= 1

        async def clear_cache(self):
            return True

    async def fake_connect(*_args, **_kw):
        nonlocal open_links, max_open
        open_links += 1
        max_open = max(max_open, open_links)
        return Link()

    monkeypatch.setattr(bleak_retry_connector, "establish_connection", fake_connect)
    monkeypatch.setattr(
        bluetooth, "async_ble_device_from_address", lambda *_a, **_k: object()
    )
    await asyncio.gather(
        *(async_send_command(None, "AA:BB", b"\xaa\x31") for _ in range(3))
    )
    assert max_open == 1
    assert writes == [True, True, True]


@pytest.mark.asyncio
async def test_send_command_retries_once_on_gatt_error(monkeypatch):
    from bleak.exc import BleakError
    import bleak_retry_connector
    from homeassistant.components import bluetooth

    from custom_components.jbl_charge5.bt import async_send_command

    attempts = []

    class Link:
        async def write_gatt_char(self, char, data, response=False):
            attempts.append(data)
            if len(attempts) == 1:
                raise BleakError("GATT error 133")

        async def disconnect(self):
            pass

        async def clear_cache(self):
            return True

    async def fake_connect(*_a, **_k):
        return Link()

    monkeypatch.setattr(bleak_retry_connector, "establish_connection", fake_connect)
    monkeypatch.setattr(
        bluetooth, "async_ble_device_from_address", lambda *_a, **_k: object()
    )
    await async_send_command(None, "CC:DD", b"\xaa\x31")
    assert len(attempts) == 2
