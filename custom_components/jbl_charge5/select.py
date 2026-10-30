"""Selects for the JBL Charge 5: PartyBoost audio channel and EQ preset."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import JblConfigEntry
from .bt import async_send_command
from .commands import (
    CHANNEL_LEFT,
    CHANNEL_MONO,
    CHANNEL_RIGHT,
    set_audio_channel,
    set_eq_custom,
    set_eq_signature,
)
from .coordinator import JblCharge5Coordinator
from .entity import JblCharge5Entity

PARALLEL_UPDATES = 1

_OPTION_TO_VALUE = {"mono": CHANNEL_MONO, "left": CHANNEL_LEFT, "right": CHANNEL_RIGHT}
_VALUE_TO_OPTION = {v: k for k, v in _OPTION_TO_VALUE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JblConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the audio-channel and EQ-preset selects."""
    async_add_entities(
        [
            JblAudioChannelSelect(entry.runtime_data),
            JblEqPresetSelect(entry.runtime_data),
        ]
    )


class JblAudioChannelSelect(JblCharge5Entity, SelectEntity):
    """Stereo channel assignment used for PartyBoost pairs (token 0x46)."""

    _attr_translation_key = "audio_channel"
    _attr_options = ["mono", "left", "right"]

    def __init__(self, coordinator: JblCharge5Coordinator) -> None:
        """Initialise with a per-speaker unique id."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_audio_channel"
        self._restored_option: str | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the last option for use until the speaker is seen."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self._attr_options:
            self._restored_option = last_state.state

    @property
    def current_option(self) -> str | None:
        """Live option when available, otherwise the restored one."""
        if self.coordinator.data is not None:
            return _VALUE_TO_OPTION.get(self.coordinator.data.channel)
        return self._restored_option

    async def async_select_option(self, option: str) -> None:
        """Send the channel to the speaker and re-read its state."""
        await async_send_command(
            self.coordinator.hass,
            self.coordinator.address,
            set_audio_channel(_OPTION_TO_VALUE[option]),
        )
        await self.coordinator.async_request_refresh()


class JblEqPresetSelect(JblAudioChannelSelect):
    """JBL Signature (EQ off) or the custom bass/mid/treble curve (0x6D/0x6E)."""

    _attr_translation_key = "eq_preset"
    _attr_options = ["signature", "custom"]

    def __init__(self, coordinator: JblCharge5Coordinator) -> None:
        """Initialise with a per-speaker unique id."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_eq_preset"

    @property
    def current_option(self) -> str | None:
        """Live preset when available, otherwise the restored one."""
        if self.coordinator.data is not None:
            return self.coordinator.data.eq_preset
        return self._restored_option

    async def async_select_option(self, option: str) -> None:
        """Switch between Signature and the current custom curve."""
        info = self.coordinator.data
        if option == "signature":
            frame = set_eq_signature()
        else:
            frame = set_eq_custom(
                (info and info.eq_bass) or 0,
                (info and info.eq_mid) or 0,
                (info and info.eq_treble) or 0,
            )
        await async_send_command(self.coordinator.hass, self.coordinator.address, frame)
        await self.coordinator.async_request_refresh()
