"""Enterprise Car Club Home Assistant integration (blueprint skeleton)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import EnterpriseCarClubCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

type EnterpriseCarClubConfigEntry = ConfigEntry[EnterpriseCarClubCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EnterpriseCarClubConfigEntry) -> bool:
    """Set up Enterprise Car Club from a config entry."""
    coordinator = EnterpriseCarClubCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EnterpriseCarClubConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
