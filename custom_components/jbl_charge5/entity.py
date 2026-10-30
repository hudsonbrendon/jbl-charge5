"""Shared entity base for JBL Charge 5."""

from __future__ import annotations

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JblCharge5Coordinator


class JblCharge5Entity(RestoreEntity, CoordinatorEntity[JblCharge5Coordinator]):
    """Base entity: shared device info + restart-safe "last known state".

    ``coordinator.data`` already keeps its last value while the speaker is
    merely out of range (see coordinator.py) — but that cache lives in
    process memory, so a Home Assistant *restart* still reborns it as
    ``None``. This base class closes that gap: it remembers, via
    ``RestoreEntity``, whether this entity had a real (non-unavailable,
    non-unknown) state before the restart, and factors that into
    ``available`` so entities keep showing their last value forever instead
    of going ``unavailable`` until the speaker is seen again.

    Subclasses that carry their own cached value (sensors via
    ``RestoreSensor``, the feedback-tones switch's ``_is_on``, etc.) restore
    that value themselves in their own ``async_added_to_hass``, always
    calling ``await super().async_added_to_hass()`` first so this base class
    records ``_restored_available`` before they run.

    The connectivity binary sensor is the deliberate exception: it never
    mixes in this restore behaviour for its ``is_on`` value, since
    connectivity is a live fact, not a value worth remembering.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: JblCharge5Coordinator) -> None:
        """Describe the speaker device and start with nothing restored."""
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
        self._restored_available = False

    async def async_added_to_hass(self) -> None:
        """Remember whether a previous run left a usable state to restore."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        self._restored_available = last_state is not None and last_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    @property
    def available(self) -> bool:
        """Stay available (showing last-known state) once we have ever had data."""
        return self.coordinator.data is not None or self._restored_available
