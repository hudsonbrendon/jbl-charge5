"""Feedback-tones switch for the JBL Charge 5 (read 0x65/0x66, set 0x67)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .bt import async_send_command
from .commands import set_feedback_tones
from .entity import JblCharge5Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the feedback-tones switch."""
    async_add_entities([JblFeedbackToneSwitch(entry.runtime_data)])


class JblFeedbackToneSwitch(JblCharge5Entity, SwitchEntity):
    """Toggle the speaker's audio feedback tones; state is read back every poll."""

    _attr_translation_key = "feedback_tones"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_feedback_tones"
        self._is_on: bool | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the last commanded state; this switch never touches BT data."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in (STATE_ON, STATE_OFF):
            self._is_on = last_state.state == STATE_ON

    @property
    def is_on(self) -> bool | None:
        if (
            self.coordinator.data is not None
            and self.coordinator.data.feedback_tones is not None
        ):
            return self.coordinator.data.feedback_tones
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set(False)

    async def _async_set(self, on: bool) -> None:
        await async_send_command(
            self.coordinator.hass, self.coordinator.address, set_feedback_tones(on)
        )
        self._is_on = on
        if self.coordinator.data is not None:
            self.coordinator.data.feedback_tones = on
        self.async_write_ha_state()
