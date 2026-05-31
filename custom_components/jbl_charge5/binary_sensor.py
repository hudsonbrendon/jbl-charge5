"""'In use' binary sensor for the JBL Charge 5 (source-connected, token 0x47)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .entity import JblCharge5Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the in-use binary sensor."""
    async_add_entities([JblInUseBinarySensor(entry.runtime_data)])


class JblInUseBinarySensor(JblCharge5Entity, BinarySensorEntity):
    """True when a Bluetooth audio source is connected (playing or paused)."""

    _attr_translation_key = "in_use"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_in_use"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.source_connected
