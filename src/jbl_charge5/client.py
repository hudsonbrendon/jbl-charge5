"""Minimal async BLE client for the JBL Charge 5 control protocol.

Only file that performs Bluetooth I/O. Decoding is delegated to the pure
protocol/tokens modules.

Empirically (recon, 2026-05-31) the speaker exposes ONE custom service with
two characteristics:
  - ...0002  write / write-without-response   -> send commands here
  - ...0001  notify / read                    -> responses arrive here
So the request and its response use DIFFERENT characteristics.
"""

import asyncio

from bleak import BleakClient, BleakScanner

from jbl_charge5.protocol import PacketType, decode_frame, encode_frame
from jbl_charge5.tokens import extract_battery

WRITE_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"
NOTIFY_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0001"


async def find_speaker(name_filter: str = "JBL") -> str:
    """Return the BLE address of the first matching speaker. Raises if none."""
    devices = await BleakScanner.discover(timeout=10.0)
    match = next(
        (d for d in devices if d.name and name_filter.lower() in d.name.lower()), None
    )
    if not match:
        raise RuntimeError(f"No BLE device matching {name_filter!r}")
    return match.address


async def read_speaker_info(address: str, timeout: float = 5.0) -> dict:
    """Connect, request Speaker Info, return {'battery': int|None, 'raw': hex}."""
    loop = asyncio.get_event_loop()
    response: asyncio.Future = loop.create_future()

    def on_notify(_handle, data: bytearray) -> None:
        try:
            frame = decode_frame(bytes(data))
        except ValueError:
            return
        if (
            frame.packet_type == PacketType.SPEAKER_INFO_RESPONSE
            and not response.done()
        ):
            response.set_result(frame)

    async with BleakClient(address) as client:
        await client.start_notify(NOTIFY_CHAR_UUID, on_notify)
        await client.write_gatt_char(
            WRITE_CHAR_UUID,
            encode_frame(PacketType.SPEAKER_INFO_REQUEST),
            response=False,
        )
        frame = await asyncio.wait_for(response, timeout=timeout)
        await client.stop_notify(NOTIFY_CHAR_UUID)

    return {"battery": extract_battery(frame.payload), "raw": frame.payload.hex()}
