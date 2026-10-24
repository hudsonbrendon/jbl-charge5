"""Sensors for the JBL Charge 5."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .entity import JblCharge5Entity
from .parser import AUDIO_SOURCES, SpeakerInfo


@dataclass(frozen=True, kw_only=True)
class JblSensorDescription(SensorEntityDescription):
    value_fn: Callable[[SpeakerInfo], str | int | None]


def _counter(
    key: str, minutes: bool = True, enabled: bool = True
) -> JblSensorDescription:
    """Lifetime counter from the speaker's analytics block (0x82)."""
    return JblSensorDescription(
        key=key,
        translation_key=key,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION if minutes else None,
        native_unit_of_measurement=UnitOfTime.MINUTES if minutes else None,
        suggested_unit_of_measurement=UnitOfTime.HOURS if minutes else None,
        entity_registry_enabled_default=enabled,
        value_fn=lambda info: info.analytics.get(key),
    )


SENSORS: tuple[JblSensorDescription, ...] = (
    JblSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda info: info.battery,
    ),
    JblSensorDescription(
        key="audio_source",
        translation_key="audio_source",
        device_class=SensorDeviceClass.ENUM,
        options=[*AUDIO_SOURCES.values()],
        value_fn=lambda info: info.source,
    ),
    JblSensorDescription(
        key="firmware",
        translation_key="firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda info: info.firmware,
    ),
    JblSensorDescription(
        key="model",
        translation_key="model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda info: None if info.model is None else f"0x{info.model:04X}",
    ),
    JblSensorDescription(
        key="mac",
        translation_key="mac",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda info: info.mac,
    ),
    _counter("play_time"),
    _counter("play_time_battery"),
    _counter("charging_time"),
    _counter("power_on_time"),
    _counter("power_on_count", minutes=False),
    _counter("critical_temperature", minutes=False),
    _counter("power_bank_time", enabled=False),
    _counter("aux_play_time", enabled=False),
    _counter("usb_pd_charging_time", enabled=False),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the JBL Charge 5 sensors."""
    coordinator = entry.runtime_data
    async_add_entities(JblSensor(coordinator, d) for d in SENSORS)


class JblSensor(JblCharge5Entity, RestoreSensor):
    """A value read from the speaker, restored across Home Assistant restarts."""

    entity_description: JblSensorDescription

    def __init__(self, coordinator, description: JblSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._restored_value: str | int | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._restored_value = last_data.native_value

    @property
    def native_value(self) -> str | int | None:
        if self.coordinator.data is not None:
            return self.entity_description.value_fn(self.coordinator.data)
        return self._restored_value
