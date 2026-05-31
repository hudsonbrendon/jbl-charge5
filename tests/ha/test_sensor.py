from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jbl_charge5.const import DOMAIN
from custom_components.jbl_charge5.parser import SpeakerInfo

ADDRESS = "10:28:74:A4:8D:E7"


@pytest.fixture(autouse=True)
def patch_bluetooth_history():
    """macOS has no D-Bus; stop LinuxAdapters.history from crashing."""
    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        return_value={},
    ):
        yield


async def _setup(hass: HomeAssistant, info: SpeakerInfo):
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="JBL Charge 5")
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.jbl_charge5.bluetooth.async_ble_device_from_address",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.jbl_charge5.coordinator.establish_connection",
            new=AsyncMock(return_value=AsyncMock()),
        ),
        patch(
            "custom_components.jbl_charge5.coordinator.async_read_speaker_info",
            new=AsyncMock(return_value=info),
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_battery_and_in_use_entities(hass: HomeAssistant):
    info = SpeakerInfo(battery=100, source_connected=True, name="JBL Charge 5")
    entry = await _setup(hass, info)

    assert entry.state is ConfigEntryState.LOADED

    battery = hass.states.get("sensor.jbl_charge_5_battery")
    assert battery is not None
    assert battery.state == "100"

    in_use = hass.states.get("binary_sensor.jbl_charge_5_in_use")
    assert in_use is not None
    assert in_use.state == "on"
