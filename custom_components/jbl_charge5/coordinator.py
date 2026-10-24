"""Coordinator that connects to the Charge 5 and polls Speaker-Info."""

from __future__ import annotations

import logging
from dataclasses import fields
from datetime import timedelta

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .bt import BLE_LOCKS, async_read_speaker_info
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
        self.device_online = False

    async def _async_update_data(self) -> SpeakerInfo:
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            self.device_online = False
            if self.data is not None:
                _LOGGER.debug(
                    "JBL %s out of range; keeping last-known state", self.address
                )
                return self.data
            raise UpdateFailed(f"JBL Charge 5 {self.address} not found / not in range")
        async with BLE_LOCKS[self.address]:
            return await self._async_poll(device)

    async def _async_poll(self, device) -> SpeakerInfo:
        client = await establish_connection(
            BleakClientWithServiceCache, device, self.address
        )
        try:
            try:
                info = await async_read_speaker_info(client)
            except BleakError as err:
                # Usually a stale GATT cache ("characteristic not found"); drop
                # it so the next poll rediscovers services.
                await client.clear_cache()
                raise UpdateFailed(f"JBL {self.address}: {err}") from err
            self.device_online = True
            if self.data is not None:
                # A reply lost in this poll keeps its last-known value.
                for f in fields(info):
                    if getattr(info, f.name) in (None, {}):
                        setattr(info, f.name, getattr(self.data, f.name))
            return info
        finally:
            await client.disconnect()
