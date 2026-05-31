"""Coordinator that connects to the Charge 5 and polls Speaker-Info."""

from __future__ import annotations

import logging
from datetime import timedelta

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .bt import async_read_speaker_info
from .const import DOMAIN, SCAN_INTERVAL_SECONDS
from .parser import SpeakerInfo

_LOGGER = logging.getLogger(__name__)


class JblCharge5Coordinator(DataUpdateCoordinator[SpeakerInfo]):
    """Connect on an interval, read Speaker-Info, expose it to entities."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.address = address

    async def _async_update_data(self) -> SpeakerInfo:
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            raise UpdateFailed(f"JBL Charge 5 {self.address} not found / not in range")
        client = await establish_connection(
            BleakClientWithServiceCache, device, self.address
        )
        try:
            return await async_read_speaker_info(client)
        finally:
            await client.disconnect()
