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
