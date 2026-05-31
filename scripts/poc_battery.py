"""Recon PoC: ask the Charge 5 for Speaker-Info and dump every notification.

Resilient first-contact version: it writes the Speaker-Info request to the
write characteristic, then prints EVERY raw notification received on the notify
characteristic for a few seconds (decoding frame type + trying battery), rather
than blocking on one expected reply. This way we learn the real response shape
even if the request guess is imperfect.
"""

import asyncio
import sys

# Recon bootstrap: make bleak + jbl_charge5 importable when launched via macOS
# `open` (LaunchServices does not forward PYTHONPATH). Harmless on Linux.
import glob
import pathlib

_root = pathlib.Path(__file__).resolve().parent.parent
for _sp in glob.glob(str(_root / ".venv/lib/python3.*/site-packages")):
    if _sp not in sys.path:
        sys.path.insert(0, _sp)
sys.path.insert(0, str(_root / "src"))

from bleak import BleakClient, BleakScanner  # noqa: E402

from jbl_charge5.protocol import PacketType, decode_frame, encode_frame  # noqa: E402
from jbl_charge5.tokens import extract_battery  # noqa: E402

WRITE_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"
NOTIFY_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0001"


async def main() -> None:
    devices = await BleakScanner.discover(timeout=10.0)
    match = next((d for d in devices if d.name and "jbl" in d.name.lower()), None)
    if not match:
        print("No JBL device found. Power the speaker on and keep it nearby.")
        return
    print(f"Speaker: {match.name} ({match.address})")

    def on_notify(_handle, data: bytearray) -> None:
        raw = bytes(data)
        line = f"  NOTIFY raw={raw.hex()}"
        try:
            frame = decode_frame(raw)
            line += f"  type=0x{frame.packet_type:02x} payload={frame.payload.hex()}"
            batt = extract_battery(frame.payload)
            if batt is not None:
                line += f"  >>> BATTERY={batt}%"
        except ValueError as exc:
            line += f"  (not a clean frame: {exc})"
        print(line)

    async with BleakClient(match.address) as client:
        await client.start_notify(NOTIFY_CHAR_UUID, on_notify)
        req = encode_frame(PacketType.SPEAKER_INFO_REQUEST)
        print(f"Writing Speaker-Info request {req.hex()} to {WRITE_CHAR_UUID}")
        await client.write_gatt_char(WRITE_CHAR_UUID, req, response=False)
        print("Listening 6s for notifications...")
        await asyncio.sleep(6.0)
        await client.stop_notify(NOTIFY_CHAR_UUID)


if __name__ == "__main__":
    asyncio.run(main())
