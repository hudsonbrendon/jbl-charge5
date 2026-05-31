"""Battery sensor for the JBL Charge 5."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .entity import JblCharge5Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the battery sensor."""
    async_add_entities([JblBatterySensor(entry.runtime_data)])


class JblBatterySensor(JblCharge5Entity, SensorEntity):
    """Battery percentage reported by the speaker (token 0x44)."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_battery"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.battery
