"""BLE I/O boundary: ask a connected Charge 5 for its Speaker-Info."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from .const import NOTIFY_CHAR_UUID, WRITE_CHAR_UUID
from .parser import SpeakerInfo, parse_speaker_info
from .protocol import PacketType, encode_frame, reassemble

# Read-only requests sent on every poll (all answered by a Charge 5, see
# docs/PROTOCOL.md). Never add the analytics *clear* (AA 01 02 82 00) the app
# sends after reading: it would wipe the speaker's lifetime counters.
POLL_REQUESTS = (
    encode_frame(PacketType.SPEAKER_INFO_REQUEST),
    encode_frame(PacketType.FIRMWARE_VERSION_REQUEST),
    encode_frame(PacketType.FEEDBACK_REQUEST),
    encode_frame(PacketType.SIMPLE_EQ_REQUEST, b"\x00"),
    encode_frame(PacketType.ANALYTICS_REQUEST),
)

# The speaker takes one BLE connection at a time: a command fired while a poll
# holds the link was silently lost (seen live), so polls and commands queue here.
BLE_LOCKS: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# The app sends one command at a time; a short gap keeps replies from piling up.
REQUEST_GAP_SECONDS = 0.3
# How long we keep listening after the last request before parsing.
COLLECT_SECONDS = 1.5


async def async_read_speaker_info(
    client, collect_seconds: float = COLLECT_SECONDS
) -> SpeakerInfo:
    """Send the poll requests and parse every notification that came back.

    `client` is an already-connected BleakClient-like object.
    """
    chunks: list[bytes] = []

    await client.start_notify(
        NOTIFY_CHAR_UUID, lambda _h, data: chunks.append(bytes(data))
    )
    try:
        for frame in POLL_REQUESTS:
            await client.write_gatt_char(WRITE_CHAR_UUID, frame, response=False)
            await asyncio.sleep(REQUEST_GAP_SECONDS)
        await asyncio.sleep(collect_seconds)
    finally:
        await client.stop_notify(NOTIFY_CHAR_UUID)

    return parse_speaker_info(reassemble(chunks))


async def async_send_command(hass, address: str, frame: bytes) -> None:
    """Connect to the speaker, write one control frame, and disconnect."""
    from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
    from homeassistant.components import bluetooth
    from homeassistant.exceptions import HomeAssistantError

    device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if device is None:
        raise HomeAssistantError(f"JBL Charge 5 {address} not in range")
    from bleak.exc import BleakError

    async with BLE_LOCKS[address]:
        for attempt in (1, 2):
            client = await establish_connection(
                BleakClientWithServiceCache, device, address
            )
            try:
                # With response, like the app: the write is acknowledged before
                # we drop the link, so it can't be lost on disconnect.
                await client.write_gatt_char(WRITE_CHAR_UUID, frame, response=True)
                return
            except BleakError:
                # A fresh proxy link sometimes fails the first GATT op (error 133).
                if attempt == 2:
                    raise
                await client.clear_cache()
            finally:
                await client.disconnect()
