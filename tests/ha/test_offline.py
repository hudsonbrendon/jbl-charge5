"""Offline behaviour: keep last-known state instead of going unavailable."""

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jbl_charge5.const import DOMAIN
from custom_components.jbl_charge5.coordinator import JblCharge5Coordinator
from custom_components.jbl_charge5.entity import JblCharge5Entity
from custom_components.jbl_charge5.parser import SpeakerInfo

ADDRESS = "10:28:74:A4:8D:E7"


def _coordinator(hass: HomeAssistant) -> JblCharge5Coordinator:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="JBL Charge 5")
    entry.add_to_hass(hass)
    return JblCharge5Coordinator(hass, entry)


@pytest.fixture(autouse=True)
def patch_bluetooth_history():
    """macOS has no D-Bus; stop LinuxAdapters.history from crashing."""
    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        return_value={},
    ):
        yield


async def test_keeps_last_known_data_when_device_goes_none(hass: HomeAssistant):
    """When the speaker drops out of range, cached data is returned (no raise)."""
    coordinator = _coordinator(hass)
    cached = SpeakerInfo(battery=77, source_connected=True, name="JBL Charge 5")
    coordinator.data = cached

    with patch(
        "custom_components.jbl_charge5.coordinator.bluetooth."
        "async_ble_device_from_address",
        return_value=None,
    ):
        result = await coordinator._async_update_data()

    assert result is cached
    assert result.battery == 77


async def test_entity_available_while_data_present(hass: HomeAssistant):
    """A base entity stays available as long as the coordinator has data."""
    coordinator = _coordinator(hass)
    coordinator.data = SpeakerInfo(battery=50, name="JBL Charge 5")

    entity = JblCharge5Entity(coordinator)
    assert entity.available is True

    coordinator.data = None
    assert entity.available is False


async def test_setup_completes_when_speaker_offline(hass: HomeAssistant):
    """Setup must still load (not hard-fail) when the speaker is out of range."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="JBL Charge 5")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.jbl_charge5.coordinator.bluetooth."
        "async_ble_device_from_address",
        return_value=None,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    # The connectivity sensor honestly reports offline.
    connectivity = hass.states.get("binary_sensor.jbl_charge_5_connectivity")
    assert connectivity is not None
    assert connectivity.state == "off"


async def test_connectivity_flips_off_when_speaker_drops_but_data_persists(
    hass: HomeAssistant,
):
    """Critical-path regression for the lying connectivity sensor.

    First a successful read populates the cache and reports online; then the
    device drops out of range. The connectivity sensor must flip to ``off``
    while the data entities stay available with their cached values.
    """
    entry = MockConfigEntry(domain=DOMAIN, unique_id=ADDRESS, title="JBL Charge 5")
    entry.add_to_hass(hass)

    info = SpeakerInfo(battery=77, source_connected=True, name="JBL Charge 5")

    # 1. Successful first refresh: cache populated, device_online True.
    with (
        patch(
            "custom_components.jbl_charge5.coordinator.bluetooth."
            "async_ble_device_from_address",
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

    assert entry.state is ConfigEntryState.LOADED
    coordinator = entry.runtime_data
    assert coordinator.device_online is True

    assert hass.states.get("binary_sensor.jbl_charge_5_connectivity").state == "on"
    assert hass.states.get("sensor.jbl_charge_5_battery").state == "77"
    assert hass.states.get("binary_sensor.jbl_charge_5_in_use").state == "on"

    # 2. The speaker drops out of range (device is None) with cache present.
    with patch(
        "custom_components.jbl_charge5.coordinator.bluetooth."
        "async_ble_device_from_address",
        return_value=None,
    ):
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    # device_online flipped off, but cached data is retained.
    assert coordinator.device_online is False
    assert coordinator.data is info

    # Connectivity honestly reports offline.
    assert hass.states.get("binary_sensor.jbl_charge_5_connectivity").state == "off"

    # Data entities stay available with their cached values.
    assert hass.states.get("sensor.jbl_charge_5_battery").state == "77"
    assert hass.states.get("binary_sensor.jbl_charge_5_in_use").state == "on"
