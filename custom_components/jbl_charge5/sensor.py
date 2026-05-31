"""Sensors for the JBL Charge 5."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .entity import JblCharge5Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the JBL Charge 5 sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            JblBatterySensor(coordinator),
            JblModelSensor(coordinator),
            JblMacSensor(coordinator),
        ]
    )


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


class JblModelSensor(JblCharge5Entity, SensorEntity):
    """Model identifier reported by the speaker (token 0x42)."""

    _attr_translation_key = "model"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_model"

    @property
    def native_value(self) -> str | None:
        model = self.coordinator.data.model
        return None if model is None else f"0x{model:04X}"


class JblMacSensor(JblCharge5Entity, SensorEntity):
    """Bluetooth MAC reported by the speaker (token 0x48)."""

    _attr_translation_key = "mac"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_mac"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.mac
