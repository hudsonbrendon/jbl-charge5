"""Diagnostics support for JBL Charge 5."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import JblConfigEntry
from .protocol import Token

# Token.MAC is the raw-token key (0x48) holding the MAC bytes.
TO_REDACT = {"unique_id", "address", "mac", Token.MAC}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: JblConfigEntry
) -> dict[str, Any]:
    """Return the entry and the last Speaker-Info snapshot, redacted."""
    coordinator = entry.runtime_data
    return async_redact_data(
        {
            "entry": {"unique_id": entry.unique_id, "data": dict(entry.data)},
            "device_online": coordinator.device_online,
            "data": asdict(coordinator.data) if coordinator.data else None,
        },
        TO_REDACT,
    )
