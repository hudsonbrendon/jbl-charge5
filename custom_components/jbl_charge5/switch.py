"""Feedback-tones switch for the JBL Charge 5 (packet 0x67, optimistic)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Toggle the speaker's audio feedback tones.

    The protocol does not return this state in the Speaker-Info burst, so the
    switch is optimistic (assumed state).
    """

    _attr_translation_key = "feedback_tones"
    _attr_assumed_state = True

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_feedback_tones"
        self._is_on: bool | None = None

    @property
    def is_on(self) -> bool | None:
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        await async_send_command(
            self.coordinator.hass, self.coordinator.address, set_feedback_tones(True)
        )
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await async_send_command(
            self.coordinator.hass, self.coordinator.address, set_feedback_tones(False)
        )
        self._is_on = False
        self.async_write_ha_state()
