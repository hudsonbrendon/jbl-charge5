"""Sensors for the JBL Charge 5."""

from __future__ import annotations

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
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


class JblBatterySensor(JblCharge5Entity, RestoreSensor):
    """Battery percentage reported by the speaker (token 0x44)."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_battery"
        self._restored_value: int | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._restored_value = last_data.native_value

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is not None:
            return self.coordinator.data.battery
        return self._restored_value


class JblModelSensor(JblCharge5Entity, RestoreSensor):
    """Model identifier reported by the speaker (token 0x42)."""

    _attr_translation_key = "model"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_model"
        self._restored_value: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._restored_value = last_data.native_value

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is not None:
            model = self.coordinator.data.model
            return None if model is None else f"0x{model:04X}"
        return self._restored_value


class JblMacSensor(JblCharge5Entity, RestoreSensor):
    """Bluetooth MAC reported by the speaker (token 0x48)."""

    _attr_translation_key = "mac"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_mac"
        self._restored_value: str | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._restored_value = last_data.native_value

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is not None:
            return self.coordinator.data.mac
        return self._restored_value
