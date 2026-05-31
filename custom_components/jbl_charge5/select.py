"""Audio-channel select for the JBL Charge 5 (PartyBoost mono/left/right)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JblConfigEntry
from .bt import async_send_command
from .commands import CHANNEL_LEFT, CHANNEL_MONO, CHANNEL_RIGHT, set_audio_channel
from .entity import JblCharge5Entity

_OPTION_TO_VALUE = {"mono": CHANNEL_MONO, "left": CHANNEL_LEFT, "right": CHANNEL_RIGHT}
_VALUE_TO_OPTION = {v: k for k, v in _OPTION_TO_VALUE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the audio-channel select."""
    async_add_entities([JblAudioChannelSelect(entry.runtime_data)])


class JblAudioChannelSelect(JblCharge5Entity, SelectEntity):
    """Stereo channel assignment used for PartyBoost pairs (token 0x46)."""

    _attr_translation_key = "audio_channel"
    _attr_options = ["mono", "left", "right"]

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_audio_channel"

    @property
    def current_option(self) -> str | None:
        return _VALUE_TO_OPTION.get(self.coordinator.data.channel)

    async def async_select_option(self, option: str) -> None:
        await async_send_command(
            self.coordinator.hass,
            self.coordinator.address,
            set_audio_channel(_OPTION_TO_VALUE[option]),
        )
        await self.coordinator.async_request_refresh()
