"""The JBL Charge 5 integration."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .coordinator import JblCharge5Coordinator

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.SELECT,
]

type JblConfigEntry = ConfigEntry[JblCharge5Coordinator]


async def async_setup_entry(hass: HomeAssistant, entry: JblConfigEntry) -> bool:
    """Set up JBL Charge 5 from a config entry."""
    address = entry.unique_id
    assert address is not None
    if bluetooth.async_ble_device_from_address(hass, address, connectable=True) is None:
        raise ConfigEntryNotReady(f"Could not find JBL Charge 5 with address {address}")

    coordinator = JblCharge5Coordinator(hass, address)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: JblConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
