"""Binary sensors for the JBL Charge 5 (in use, charging, connectivity)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON
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
            JblChargingBinarySensor(coordinator),
            JblConnectivityBinarySensor(coordinator),
        ]
    )


class JblInUseBinarySensor(JblCharge5Entity, BinarySensorEntity):
    """True when an audio source (Bluetooth or AUX) is connected, playing or paused."""

    _attr_translation_key = "in_use"
    _key = "in_use"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{self._key}"
        self._restored_is_on: bool | None = None

    def _value(self, info) -> bool | None:
        return info.source_connected

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in (STATE_ON, STATE_OFF):
            self._restored_is_on = last_state.state == STATE_ON

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is not None:
            return self._value(self.coordinator.data)
        return self._restored_is_on


class JblChargingBinarySensor(JblInUseBinarySensor):
    """Charger plugged in: bit 7 of the battery token 0x44."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_translation_key = None
    _key = "charging"

    def _value(self, info) -> bool | None:
        return info.charging


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
        return self.coordinator.device_online
