"""The JBL Charge 5 integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import JblCharge5Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]

type JblConfigEntry = ConfigEntry[JblCharge5Coordinator]


async def async_setup_entry(hass: HomeAssistant, entry: JblConfigEntry) -> bool:
    """Set up JBL Charge 5 from a config entry."""
    address = entry.unique_id
    assert address is not None

    coordinator = JblCharge5Coordinator(hass, address)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        _LOGGER.debug("JBL %s offline at setup; loading with no cached state", address)
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JblConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
