"""Services for the enterprise_carclub integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import probatio as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import EnterpriseCarClubCoordinator, isoformat_epoch

SERVICE_CHECK_AVAILABILITY = "check_availability"
SERVICE_BOOK_VEHICLE = "book_vehicle"

SERVICE_BOOK_SCHEMA = vol.Schema(
    {
        vol.Required("stack_id"): str,
        vol.Required("start"): cv.datetime,
        vol.Required("end"): cv.datetime,
        vol.Optional("memo", default=""): str,
    }
)

SERVICE_CHECK_SCHEMA = vol.Schema(
    {
        vol.Required("stack_id"): str,
        vol.Required("start"): cv.datetime,
        vol.Required("end"): cv.datetime,
    }
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services (called once from async_setup)."""
    if hass.data.get(DOMAIN):
        return
    hass.data[DOMAIN] = True

    async def _get_client() -> tuple[EnterpriseCarClubCoordinator, Any]:
        from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

        coordinator: EnterpriseCarClubCoordinator | None = None
        for entry in hass.config_entries.async_entries(DOMAIN):
            runtime_data = getattr(entry, "runtime_data", None)
            if runtime_data is not None:
                coordinator = runtime_data
                break
        if coordinator is None:
            raise HomeAssistantError("Enterprise Car Club is not set up")
        client = coordinator._get_client()
        if client.token is None:
            await client.async_login(
                coordinator.entry.data[CONF_USERNAME],
                coordinator.entry.data[CONF_PASSWORD],
            )
        return coordinator, client

    async def handle_check_availability(call: ServiceCall) -> dict[str, Any]:
        _, client = await _get_client()
        start: datetime = call.data["start"]
        end: datetime = call.data["end"]
        slots = await client.async_get_stack_timeslots(
            call.data["stack_id"],
            start_time=int(start.timestamp()),
            end_time=int(end.timestamp()),
        )
        return {
            "stack_id": call.data["stack_id"],
            "timeslots": [
                {
                    "time": isoformat_epoch(s["time"]) if isinstance(s.get("time"), int) else s.get("time"),
                    "available": s.get("available"),
                }
                for s in slots
            ],
        }

    async def handle_book_vehicle(call: ServiceCall) -> dict[str, Any]:
        _, client = await _get_client()
        start: datetime = call.data["start"]
        end: datetime = call.data["end"]
        reservation = await client.async_make_reservation(
            call.data["stack_id"],
            start_time=int(start.timestamp()),
            end_time=int(end.timestamp()),
            memo=call.data.get("memo", ""),
        )
        estimate = reservation.get("estimate_unformatted") or {}
        amount = estimate.get("currency_amount") if isinstance(estimate, dict) else None
        return {
            "reservation_id": reservation.get("id"),
            "status": reservation.get("status"),
            "total": (amount or {}).get("value") if isinstance(amount, dict) else None,
            "currency": (amount or {}).get("currency_code") if isinstance(amount, dict) else None,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_AVAILABILITY,
        handle_check_availability,
        schema=SERVICE_CHECK_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_BOOK_VEHICLE,
        handle_book_vehicle,
        schema=SERVICE_BOOK_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
