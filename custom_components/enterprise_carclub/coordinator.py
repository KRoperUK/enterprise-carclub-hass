"""Data update coordinator for the enterprise_carclub integration."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from enterprise_carclub import AuthError, Client, ClientError, summarize_stack

from .const import (
    CONF_MARKET_ID,
    CONF_WINDOW_HOURS,
    DEFAULT_MARKET_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_WINDOW_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def next_quarter_epoch(from_epoch: int | None = None) -> int:
    """Round up to the next 15-minute boundary (API requirement)."""
    base = from_epoch if from_epoch is not None else int(time.time())
    return ((base // 900) + 1) * 900


def isoformat_epoch(epoch: int) -> str:
    """Format epoch seconds as an ISO-8601 UTC string."""
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat()


class EnterpriseCarClubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch reservations, messages and nearby vehicles for one account."""

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

    def _search_params(self) -> dict[str, Any]:
        options = self.entry.options
        latitude = options.get(CONF_LATITUDE, self.hass.config.latitude)
        longitude = options.get(CONF_LONGITUDE, self.hass.config.longitude)
        window_hours = options.get(CONF_WINDOW_HOURS, DEFAULT_WINDOW_HOURS)
        market_id = options.get(CONF_MARKET_ID, DEFAULT_MARKET_ID)
        start = next_quarter_epoch()
        return {
            "latitude": latitude,
            "longitude": longitude,
            "market_id": market_id,
            "start_time": start,
            "end_time": start + int(window_hours) * 3600,
        }

    @staticmethod
    def _reservation_by_stack(reservations: Any) -> dict[str, dict[str, Any]]:
        """Index future reservations by their vehicle stack id."""
        index: dict[str, dict[str, Any]] = {}
        if not isinstance(reservations, list):
            return index
        for reservation in reservations:
            if not isinstance(reservation, dict):
                continue
            stack = reservation.get("vehicle_stack")
            stack_id = stack.get("id") if isinstance(stack, dict) else None
            if isinstance(stack_id, str):
                index[stack_id] = reservation
        return index

    def _summarize_stacks(
        self, stacks: list[dict[str, Any]], reservations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        by_stack = self._reservation_by_stack(reservations)
        summaries = []
        for entry in stacks:
            if not isinstance(entry, dict):
                continue
            summary = summarize_stack(entry)
            reservation = by_stack.get(str(summary.get("stack_id")))
            if reservation is not None:
                start = reservation.get("start_timestamp")
                end = reservation.get("end_timestamp")
                summary["reservation"] = {
                    "id": reservation.get("id"),
                    "status": reservation.get("status"),
                    "start": isoformat_epoch(start) if isinstance(start, int) else start,
                    "end": isoformat_epoch(end) if isinstance(end, int) else end,
                }
            else:
                summary["reservation"] = None
            slots = summary.get("timeslots")
            if isinstance(slots, list):
                summary["timeslots"] = [
                    {
                        "time": isoformat_epoch(s["time"]) if isinstance(s.get("time"), int) else s.get("time"),
                        "available": s.get("available"),
                    }
                    for s in slots
                    if isinstance(s, dict)
                ]
            if isinstance(summary.get("next_free_time"), int):
                summary["next_free_time"] = isoformat_epoch(summary["next_free_time"])
            summaries.append(summary)
        return summaries

    async def _fetch(self, client: Client) -> dict[str, Any]:
        reservations = await client.async_get_current_and_future()
        messages = await client.async_get_driver_messages()
        params = self._search_params()
        stacks = await client.async_search_stacks(
            latitude=params["latitude"],
            longitude=params["longitude"],
            start_time=params["start_time"],
            end_time=params["end_time"],
            market_id=params["market_id"],
        )
        return {
            "reservations": reservations,
            "messages": messages,
            "vehicles": self._summarize_stacks(stacks, reservations),
            "search_params": params,
            "source": "cloud",
        }

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
