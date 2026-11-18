"""Binary sensors for favorite Enterprise Car Club vehicles."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FAVORITE_STACK_IDS, DOMAIN
from .coordinator import EnterpriseCarClubCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up one availability sensor per favorite vehicle."""
    coordinator: EnterpriseCarClubCoordinator = entry.runtime_data
    favorites = entry.options.get(CONF_FAVORITE_STACK_IDS, [])
    async_add_entities(
        [EnterpriseCarClubFavoriteAvailableSensor(coordinator, entry, stack_id) for stack_id in favorites]
    )


class EnterpriseCarClubFavoriteAvailableSensor(CoordinatorEntity[EnterpriseCarClubCoordinator], BinarySensorEntity):
    """Availability of one favorite vehicle stack."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry, stack_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._stack_id = stack_id
        self._attr_unique_id = f"{entry.unique_id}_fav_{stack_id}"
        self._attr_name = f"Favorite {stack_id} available"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id or entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Enterprise Car Club",
        }

    def _vehicle(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        if not data:
            return None
        for vehicle in data.get("vehicles", []):
            if isinstance(vehicle, dict) and vehicle.get("stack_id") == self._stack_id:
                return vehicle
        return None

    @property
    def is_on(self) -> bool | None:
        """Return True when the favorite currently shows good availability."""
        vehicle = self._vehicle()
        if vehicle is None:
            return None
        return vehicle.get("availability") == "good"

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the vehicle summary alongside availability."""
        vehicle = self._vehicle()
        if vehicle is None:
            return {"stack_id": self._stack_id, "present": False}
        attributes = dict(vehicle)
        attributes["present"] = True
        return attributes
