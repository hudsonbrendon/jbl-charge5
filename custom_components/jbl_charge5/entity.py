"""Shared entity base for JBL Charge 5."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JblCharge5Coordinator


class JblCharge5Entity(CoordinatorEntity[JblCharge5Coordinator]):
    """Base entity with shared device info."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: JblCharge5Coordinator) -> None:
        super().__init__(coordinator)
        address = coordinator.address
        info = coordinator.data
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, address)},
            identifiers={(DOMAIN, address)},
            manufacturer="JBL",
            model=(info.name if info and info.name else "Charge 5"),
            name=(info.name if info and info.name else "JBL Charge 5"),
        )
