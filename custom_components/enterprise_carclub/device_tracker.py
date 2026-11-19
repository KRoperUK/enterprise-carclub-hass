"""Device trackers placing nearby Enterprise Car Club vehicles on the map."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.device_tracker.entity import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .binary_sensor import vehicle_display_name
from .const import DOMAIN
from .coordinator import EnterpriseCarClubCoordinator

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up one tracker per vehicle in the latest search."""
    coordinator: EnterpriseCarClubCoordinator = entry.runtime_data
    vehicles = (coordinator.data or {}).get("vehicles", [])
    async_add_entities(
        [
            EnterpriseCarClubVehicleTracker(coordinator, entry, vehicle)
            for vehicle in vehicles
            if isinstance(vehicle, dict) and isinstance(vehicle.get("stack_id"), str)
        ]
    )


class EnterpriseCarClubVehicleTracker(CoordinatorEntity[EnterpriseCarClubCoordinator], TrackerEntity):
    """A bookable vehicle plotted at its bay location."""

    _attr_has_entity_name = True
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry, vehicle: dict[str, Any]) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._stack_id = vehicle["stack_id"]
        self._attr_unique_id = f"{entry.unique_id}_stack_{self._stack_id}"
        self._attr_name = vehicle_display_name(vehicle, self._stack_id)
        self._attr_device_info = {  # type: ignore[assignment]
            "identifiers": {(DOMAIN, f"stack_{self._stack_id}")},
            "name": vehicle.get("description") or f"Vehicle {self._stack_id}",
            "manufacturer": "Enterprise Car Club",
            "model": vehicle.get("make_model"),
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
    def latitude(self) -> float | None:
        """Return the bay latitude."""
        vehicle = self._vehicle()
        lat = vehicle.get("latitude") if vehicle else None
        return lat if isinstance(lat, (int, float)) else None

    @property
    def longitude(self) -> float | None:
        """Return the bay longitude."""
        vehicle = self._vehicle()
        lon = vehicle.get("longitude") if vehicle else None
        return lon if isinstance(lon, (int, float)) else None

    @property
    def entity_picture(self) -> str | None:
        """Return the vehicle preview photo for the map view."""
        vehicle = self._vehicle()
        if not vehicle:
            return None
        thumb = vehicle.get("thumb_url")
        return thumb if isinstance(thumb, str) and thumb.startswith("http") else None

    @staticmethod
    def _battery_level(vehicle: dict[str, Any]) -> int | None:
        """Return the EV battery percentage when reported."""
        try:
            return int(str(vehicle.get("battery_level")))
        except TypeError, ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose booking-relevant summary attributes."""
        vehicle = self._vehicle()
        if vehicle is None:
            return {"stack_id": self._stack_id, "present": False}
        return {
            "stack_id": vehicle.get("stack_id"),
            "battery_level": self._battery_level(vehicle),
            "size_class": vehicle.get("size_class"),
            "fuel": vehicle.get("fuel"),
            "seats": vehicle.get("seats"),
            "availability": vehicle.get("availability"),
            "distance_m": vehicle.get("distance_m"),
            "next_free_time": vehicle.get("next_free_time"),
            "present": True,
        }
