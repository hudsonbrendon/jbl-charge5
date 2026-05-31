"""Recon: find the JBL Charge 5 over BLE and dump its GATT table.

Usage:
    .venv/bin/python scripts/scan.py            # list all BLE devices
    .venv/bin/python scripts/scan.py "JBL"      # connect to first match, dump GATT
"""

import asyncio
import sys

# Recon bootstrap: when launched via macOS `open` (LaunchServices), PYTHONPATH
# is not forwarded, so add the project venv's site-packages relative to this
# file. Harmless when bleak is already importable (e.g. on Linux).
import glob
import pathlib

_root = pathlib.Path(__file__).resolve().parent.parent
for _sp in glob.glob(str(_root / ".venv/lib/python3.*/site-packages")):
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

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
