import asyncio

import pytest

from custom_components.jbl_charge5 import const
from custom_components.jbl_charge5.bt import async_read_speaker_info

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
