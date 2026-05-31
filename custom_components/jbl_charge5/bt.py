"""BLE I/O boundary: ask a connected Charge 5 for its Speaker-Info."""

from __future__ import annotations

import asyncio

from .const import NOTIFY_CHAR_UUID, WRITE_CHAR_UUID
from .parser import SpeakerInfo, parse_speaker_info
from .protocol import PacketType, decode_frame, encode_frame

# The speaker answers the AA11 request with a quick burst; this is how long we
# listen for notifications before parsing what arrived.
COLLECT_SECONDS = 2.0


async def async_read_speaker_info(
    client, collect_seconds: float = COLLECT_SECONDS
) -> SpeakerInfo:
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
            WRITE_CHAR_UUID,
            encode_frame(PacketType.SPEAKER_INFO_REQUEST),
            response=False,
        )
        await asyncio.sleep(collect_seconds)
    finally:
        await client.stop_notify(NOTIFY_CHAR_UUID)

    return parse_speaker_info(frames)


async def async_send_command(hass, address: str, frame: bytes) -> None:
    """Connect to the speaker, write one control frame, and disconnect."""
    from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
    from homeassistant.components import bluetooth
    from homeassistant.exceptions import HomeAssistantError

    device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
    if device is None:
        raise HomeAssistantError(f"JBL Charge 5 {address} not in range")
    client = await establish_connection(BleakClientWithServiceCache, device, address)
    try:
        await client.write_gatt_char(WRITE_CHAR_UUID, frame, response=False)
    finally:
        await client.disconnect()
