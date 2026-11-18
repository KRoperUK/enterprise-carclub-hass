"""Enterprise Car Club Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import EnterpriseCarClubCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.DEVICE_TRACKER]

type EnterpriseCarClubConfigEntry = ConfigEntry[EnterpriseCarClubCoordinator]


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options (search area, favorites) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: EnterpriseCarClubConfigEntry) -> bool:
    """Set up Enterprise Car Club from a config entry."""
    coordinator = EnterpriseCarClubCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EnterpriseCarClubConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
