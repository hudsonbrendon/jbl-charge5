from unittest.mock import patch

import pytest
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import SOURCE_BLUETOOTH
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.jbl_charge5.const import DOMAIN, SERVICE_UUID

SERVICE_INFO = BluetoothServiceInfoBleak(
    name="JBL Charge 5",
    address="10:28:74:A4:8D:E7",
    rssi=-50,
    manufacturer_data={},
    service_data={},
    service_uuids=[SERVICE_UUID],
    source="local",
    device=None,
    advertisement=None,
    connectable=True,
    time=0,
    tx_power=-127,
)


@pytest.fixture(autouse=True)
def patch_bluetooth_history():
    """Patch LinuxAdapters.history to avoid D-Bus on macOS."""
    with patch(
        "bluetooth_adapters.systems.linux.LinuxAdapters.history",
        new_callable=lambda: property(lambda self: {}),
    ):
        yield


async def test_bluetooth_discovery_flow(hass: HomeAssistant, mock_bluetooth):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=SERVICE_INFO
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    with patch(
        "custom_components.jbl_charge5.async_setup_entry", return_value=True
    ):
        result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "JBL Charge 5"
    assert result2["result"].unique_id == "10:28:74:A4:8D:E7"
