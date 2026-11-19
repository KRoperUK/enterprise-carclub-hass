"""Diagnostics support for the enterprise_carclub integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

TO_REDACT = {"password", "token", "authorization_token", "login_token"}


def _redacted(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: ("**REDACTED**" if key in TO_REDACT else _redacted(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redacted(item) for item in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (credentials redacted)."""
    coordinator = entry.runtime_data
    data = getattr(coordinator, "data", None)
    devices: list[dict[str, Any]] = []
    registry = dr.async_get(hass)
    for device_entry in dr.async_entries_for_config_entry(registry, entry.entry_id):
        devices.append(
            {
                "name": device_entry.name,
                "manufacturer": device_entry.manufacturer,
                "model": device_entry.model,
            }
        )
    return {
        "entry": {
            "title": entry.title,
            "username": entry.data.get("username"),
            "options": dict(entry.options),
        },
        "data": _redacted(data),
        "devices": devices,
    }
