"""Custom EQ bands (bass / mid / treble) for the JBL Charge 5 (0x6D read, 0x6E set)."""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import JblConfigEntry
from .bt import async_send_command
from .commands import set_eq_custom
from .coordinator import JblCharge5Coordinator
from .entity import JblCharge5Entity

PARALLEL_UPDATES = 1

BANDS = ("eq_bass", "eq_mid", "eq_treble")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one number per EQ band."""
    async_add_entities(JblEqBand(entry.runtime_data, band) for band in BANDS)


class JblEqBand(JblCharge5Entity, RestoreNumber):
    """One band of the custom EQ. Changing it switches the speaker to "custom"."""

    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: JblCharge5Coordinator, band: str) -> None:
        """Initialise the slider for ``band`` (one of ``BANDS``)."""
        super().__init__(coordinator)
        self._band = band
        self._attr_translation_key = band
        self._attr_unique_id = f"{coordinator.address}_{band}"
        self._restored_value: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the last level for use until the speaker is seen."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) is not None:
            self._restored_value = last.native_value

    @property
    def _scope(self) -> int:
        # The speaker reports its range (Charge 5: 2 -> levels -2..+2).
        data = self.coordinator.data
        return (data and data.eq_scope) or 2

    @property
    def native_min_value(self) -> float:
        """Lowest level the speaker accepts."""
        return -self._scope

    @property
    def native_max_value(self) -> float:
        """Highest level the speaker accepts."""
        return self._scope

    @property
    def native_value(self) -> float | None:
        """Live level when available, otherwise the restored one."""
        if self.coordinator.data is not None:
            return getattr(self.coordinator.data, self._band)
        return self._restored_value

    async def async_set_native_value(self, value: float) -> None:
        """Send the whole custom curve with this band changed."""
        data = self.coordinator.data
        levels = {b: (getattr(data, b) if data else None) or 0 for b in BANDS}
        levels[self._band] = int(value)
        await async_send_command(
            self.coordinator.hass,
            self.coordinator.address,
            set_eq_custom(levels["eq_bass"], levels["eq_mid"], levels["eq_treble"]),
        )
        if data is not None:
            setattr(data, self._band, int(value))
            data.eq_preset = "custom"
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
