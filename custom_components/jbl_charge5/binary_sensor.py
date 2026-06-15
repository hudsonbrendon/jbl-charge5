"""'In use' binary sensor for the JBL Charge 5 (source-connected, token 0x47)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .entity import JblCharge5Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            JblInUseBinarySensor(coordinator),
            JblConnectivityBinarySensor(coordinator),
        ]
    )


class JblInUseBinarySensor(JblCharge5Entity, BinarySensorEntity):
    """True when a Bluetooth audio source is connected (playing or paused)."""

    _attr_translation_key = "in_use"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_in_use"

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.source_connected


class JblConnectivityBinarySensor(JblCharge5Entity, BinarySensorEntity):
    """Honest online/offline state of the speaker's BLE link.

    Unlike the other entities, this one is always available so it can keep
    reporting "off" while the speaker is out of range. ``is_on`` reflects
    whether the most recent coordinator refresh succeeded.
    """

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "connectivity"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_connectivity"

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.coordinator.last_update_success
