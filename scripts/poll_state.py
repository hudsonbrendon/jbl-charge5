"""Recon: poll Speaker-Info repeatedly to catch play/pause-related changes.

Sends 0xAA11 every 2s for ~16s and prints, per round, the audio-source token
(0x47), battery (0x44), and any token whose value changed since the previous
round. Toggle play/pause on the speaker during the window to see what moves.
"""

import asyncio
import sys

import glob
import pathlib

_root = pathlib.Path(__file__).resolve().parent.parent
for _sp in glob.glob(str(_root / ".venv/lib/python3.*/site-packages")):
    if _sp not in sys.path:
        sys.path.insert(0, _sp)
sys.path.insert(0, str(_root / "src"))

from bleak import BleakClient, BleakScanner  # noqa: E402

from jbl_charge5.protocol import PacketType, decode_frame, encode_frame  # noqa: E402

WRITE_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0002"
NOTIFY_CHAR_UUID = "65786365-6c70-6f69-6e74-2e636f6d0001"
ROUNDS = 8


async def main() -> None:
    devices = await BleakScanner.discover(timeout=10.0)
    match = next((d for d in devices if d.name and "jbl" in d.name.lower()), None)
    if not match:
        print("No JBL device found. Power the speaker on and keep it nearby.")
        return
    print(f"Speaker: {match.name} ({match.address})")
    print("Toggle PLAY / PAUSE on the speaker during the next ~16 seconds.\n")

    # token byte -> last seen value (hex), to detect changes between rounds
    last: dict[int, str] = {}

    def collect(store: dict[int, str]):
        def on_notify(_handle, data: bytearray) -> None:
            try:
                frame = decode_frame(bytes(data))
            except ValueError:
                return
            p = frame.payload
            # payload shape: 00 <token> [len] <value...>; record token -> value hex
            if len(p) >= 3 and p[0] == 0x00:
                store[p[1]] = p[2:].hex()
        return on_notify

    async with BleakClient(match.address) as client:
        for rnd in range(1, ROUNDS + 1):
            current: dict[int, str] = {}
            await client.start_notify(NOTIFY_CHAR_UUID, collect(current))
            await client.write_gatt_char(
                WRITE_CHAR_UUID, encode_frame(PacketType.SPEAKER_INFO_REQUEST), response=False
            )
            await asyncio.sleep(2.0)
            await client.stop_notify(NOTIFY_CHAR_UUID)

            src = current.get(0x47, "?")
            batt = current.get(0x44, "?")
            changed = {
                f"0x{t:02x}": f"{last[t]}->{v}"
                for t, v in current.items()
                if t in last and last[t] != v
            }
            line = f"round {rnd}: audio_source(0x47)={src}  battery(0x44)={batt}"
            if changed:
                line += f"  CHANGED={changed}"
            print(line)
            last.update(current)


if __name__ == "__main__":
    asyncio.run(main())
