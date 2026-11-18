"""Data update coordinator for the enterprise_carclub integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from enterprise_carclub import AuthError, Client, ClientError

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EnterpriseCarClubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch reservations and messages for one Enterprise Car Club account."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self._client: Client | None = None

    def _get_client(self) -> Client:
        if self._client is None:
            self._client = Client(async_get_clientsession(self.hass))
        return self._client

    async def _fetch(self, client: Client) -> dict[str, Any]:
        reservations = await client.async_get_current_and_future()
        messages = await client.async_get_driver_messages()
        return {"reservations": reservations, "messages": messages, "source": "cloud"}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the Enterprise Car Club API."""
        client = self._get_client()
        username = self.entry.data[CONF_USERNAME]
        password = self.entry.data[CONF_PASSWORD]
        try:
            if client.token is None:
                await client.async_login(username, password)
            try:
                return await self._fetch(client)
            except AuthError:
                await client.async_login(username, password)
                return await self._fetch(client)
        except AuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
        except ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
