"""Find-my-speaker button for the JBL Charge 5."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import JblConfigEntry
from .bt import async_send_command
from .commands import play_sound
from .coordinator import JblCharge5Coordinator
from .entity import JblCharge5Entity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the play-sound button."""
    async_add_entities([JblPlaySoundButton(entry.runtime_data)])


class JblPlaySoundButton(JblCharge5Entity, ButtonEntity):
    """Plays the speaker's tone so you can find it (packet 0x31)."""

    _attr_translation_key = "play_sound"

    def __init__(self, coordinator: JblCharge5Coordinator) -> None:
        """Initialise with a per-speaker unique id."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_play_sound"

    async def async_press(self) -> None:
        """Send the play-sound command."""
        await async_send_command(
            self.coordinator.hass, self.coordinator.address, play_sound()
        )
