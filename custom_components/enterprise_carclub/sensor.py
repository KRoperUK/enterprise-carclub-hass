"""Sensor platform for the enterprise_carclub integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnterpriseCarClubCoordinator

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Enterprise Car Club sensors."""
    coordinator: EnterpriseCarClubCoordinator = entry.runtime_data
    async_add_entities(
        [
            EnterpriseCarClubReservationsSensor(coordinator, entry),
            EnterpriseCarClubMessagesSensor(coordinator, entry),
        ]
    )


class _BaseSensor(CoordinatorEntity[EnterpriseCarClubCoordinator], SensorEntity):
    """Shared device info and count helper."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry, key: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_{key}"
        self._key = key
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id or entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Enterprise Car Club",
        }

    def _count(self, field: str) -> int | None:
        data = self.coordinator.data
        if not data:
            return None
        items = data.get(field)
        return len(items) if isinstance(items, list) else None


class EnterpriseCarClubReservationsSensor(_BaseSensor):
    """Number of upcoming reservations on the account."""

    _attr_name = "Upcoming reservations"
    _attr_native_unit_of_measurement = "reservations"

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "reservations")

    @property
    def native_value(self) -> int | None:
        """Return the reservation count."""
        return self._count("reservations")


class EnterpriseCarClubMessagesSensor(_BaseSensor):
    """Number of driver inbox messages."""

    _attr_name = "Driver messages"
    _attr_native_unit_of_measurement = "messages"

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "messages")

    @property
    def native_value(self) -> int | None:
        """Return the message count."""
        return self._count("messages")
