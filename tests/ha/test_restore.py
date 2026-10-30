"""Restore-on-restart: the last known value must survive a full HA restart.

``test_offline.py`` covers staying available while the speaker is merely out
of range *within one running HA process* (``coordinator.data`` lives in
memory and is simply not cleared). This file covers the harder case: a full
Home Assistant restart reborns ``coordinator.data`` as ``None`` before the
speaker is ever seen again, so the previous run's last value has to come
back from Home Assistant's restore-state storage instead.
"""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, State
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
    mock_restore_cache_with_extra_data,
)

from custom_components.jbl_charge5.const import DOMAIN

ADDRESS = "10:28:74:A4:8D:E7"


@pytest.fixture(autouse=True)
def patch_bluetooth_history():
    """macOS has no D-Bus; stop LinuxAdapters.history from crashing."""
    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        return_value={},
    ):
        yield


async def _setup_with_device_off(hass: HomeAssistant) -> MockConfigEntry:
    """Load the integration as if the speaker were off across the restart."""
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
    return entry


async def test_battery_sensor_restores_last_value_after_restart(hass: HomeAssistant):
    """Battery must show its pre-restart value, not go unavailable forever."""
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State("sensor.jbl_charge_5_battery", "77"),
                {"native_value": 77, "native_unit_of_measurement": "%"},
            ),
        ),
    )

    await _setup_with_device_off(hass)

    battery = hass.states.get("sensor.jbl_charge_5_battery")
    assert battery is not None
    assert battery.state == "77"


async def test_model_and_mac_sensors_restore_after_restart(hass: HomeAssistant):
    """Diagnostic string sensors restore their already-formatted last value."""
    mock_restore_cache_with_extra_data(
        hass,
        (
            (
                State("sensor.jbl_charge_5_model", "0x0221"),
                {"native_value": "0x0221", "native_unit_of_measurement": None},
            ),
            (
                State("sensor.jbl_charge_5_mac_address", "10:28:74:a4:8d:e7"),
                {
                    "native_value": "10:28:74:a4:8d:e7",
                    "native_unit_of_measurement": None,
                },
            ),
        ),
    )

    await _setup_with_device_off(hass)

    assert hass.states.get("sensor.jbl_charge_5_model").state == "0x0221"
    mac_sensor = hass.states.get("sensor.jbl_charge_5_mac_address")
    assert mac_sensor.state == "10:28:74:a4:8d:e7"


async def test_in_use_binary_sensor_restores_after_restart(hass: HomeAssistant):
    """The 'source connected' binary sensor restores its last on/off."""
    mock_restore_cache(hass, [State("binary_sensor.jbl_charge_5_in_use", "on")])

    await _setup_with_device_off(hass)

    in_use = hass.states.get("binary_sensor.jbl_charge_5_in_use")
    assert in_use is not None
    assert in_use.state == "on"


async def test_audio_channel_select_restores_after_restart(hass: HomeAssistant):
    """The PartyBoost channel select restores its last chosen option."""
    mock_restore_cache(hass, [State("select.jbl_charge_5_audio_channel", "left")])

    await _setup_with_device_off(hass)

    select_state = hass.states.get("select.jbl_charge_5_audio_channel")
    assert select_state is not None
    assert select_state.state == "left"


async def test_feedback_tone_switch_restores_after_restart(hass: HomeAssistant):
    """The optimistic feedback-tones switch restores its last commanded state."""
    mock_restore_cache(hass, [State("switch.jbl_charge_5_feedback_tones", "on")])

    await _setup_with_device_off(hass)

    switch_state = hass.states.get("switch.jbl_charge_5_feedback_tones")
    assert switch_state is not None
    assert switch_state.state == "on"


async def test_play_sound_button_stays_available_after_restart(hass: HomeAssistant):
    """The button has no cached value, but must not go unavailable forever."""
    mock_restore_cache(
        hass,
        [State("button.jbl_charge_5_play_sound", "2024-01-01T00:00:00+00:00")],
    )

    await _setup_with_device_off(hass)

    button_state = hass.states.get("button.jbl_charge_5_play_sound")
    assert button_state is not None
    assert button_state.state != "unavailable"


async def test_connectivity_never_restores_a_stale_on(hass: HomeAssistant):
    """Connectivity must report the honest, live state, never a restored 'on'."""
    mock_restore_cache(hass, [State("binary_sensor.jbl_charge_5_connectivity", "on")])

    await _setup_with_device_off(hass)

    connectivity = hass.states.get("binary_sensor.jbl_charge_5_connectivity")
    assert connectivity is not None
    assert connectivity.state == "off"
