"""Sensor platform for the enterprise_carclub integration."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EnterpriseCarClubCoordinator, isoformat_epoch

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Enterprise Car Club sensors."""
    coordinator: EnterpriseCarClubCoordinator = entry.runtime_data
    async_add_entities(
        [
            EnterpriseCarClubReservationsSensor(coordinator, entry),
            EnterpriseCarClubMessagesSensor(coordinator, entry),
            EnterpriseCarClubAvailableVehiclesSensor(coordinator, entry),
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

    def _items(self, field: str) -> list[dict[str, Any]] | None:
        data = self.coordinator.data
        if not data:
            return None
        items = data.get(field)
        return items if isinstance(items, list) else None


class EnterpriseCarClubReservationsSensor(_BaseSensor):
    """Number of upcoming reservations on the account."""

    _attr_translation_key = "upcoming_reservations"
    _attr_native_unit_of_measurement = "reservations"

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "reservations")

    @property
    def native_value(self) -> int | None:
        """Return the reservation count."""
        items = self._items("reservations")
        return len(items) if items is not None else None

    @staticmethod
    def _reservation_start(reservation: dict[str, Any]) -> int:
        start = reservation.get("start_timestamp")
        return start if isinstance(start, int) else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the soonest upcoming reservation with vehicle and cost."""
        items = self._items("reservations")
        if not items:
            return None if items is None else {"next_reservation": None}
        upcoming = sorted(
            (r for r in items if isinstance(r, dict)),
            key=EnterpriseCarClubReservationsSensor._reservation_start,
        )
        if not upcoming:
            return {"next_reservation": None}
        first = upcoming[0]
        raw_stack = first.get("vehicle_stack")
        stack: dict[str, Any] = raw_stack if isinstance(raw_stack, dict) else {}
        raw_estimate = first.get("estimate_unformatted")
        estimate: dict[str, Any] = raw_estimate if isinstance(raw_estimate, dict) else {}
        raw_amount = estimate.get("currency_amount")
        amount: dict[str, Any] = raw_amount if isinstance(raw_amount, dict) else {}
        raw_details = stack.get("vehicle_details")
        details: dict[str, Any] = raw_details if isinstance(raw_details, dict) else {}
        start = first.get("start_timestamp")
        end = first.get("end_timestamp")
        return {
            "next_reservation": {
                "id": first.get("id"),
                "status": first.get("status"),
                "start": isoformat_epoch(start) if isinstance(start, int) else start,
                "end": isoformat_epoch(end) if isinstance(end, int) else end,
                "make_model": stack.get("make_model"),
                "location": stack.get("lot_description"),
                "plate": details.get("plate"),
                "total": amount.get("value"),
                "currency": amount.get("currency_code"),
            }
        }


class EnterpriseCarClubMessagesSensor(_BaseSensor):
    """Number of driver inbox messages."""

    _attr_translation_key = "driver_messages"
    _attr_native_unit_of_measurement = "messages"

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "messages")

    @property
    def native_value(self) -> int | None:
        """Return the message count."""
        items = self._items("messages")
        return len(items) if items is not None else None


class EnterpriseCarClubAvailableVehiclesSensor(_BaseSensor):
    """Number of nearby vehicles currently showing good availability."""

    _attr_translation_key = "available_vehicles"
    _attr_native_unit_of_measurement = "vehicles"

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, "vehicles")

    def _available(self) -> list[dict[str, Any]] | None:
        items = self._items("vehicles")
        if items is None:
            return None
        return [v for v in items if isinstance(v, dict) and v.get("availability") == "good"]

    @property
    def native_value(self) -> int | None:
        """Return the available-vehicle count."""
        available = self._available()
        return len(available) if available is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose per-vehicle summaries plus size-class and fuel breakdowns.

        Full timeslot lists stay out of state attributes (recorder 16 kB
        limit) — use the ``check_availability`` service for schedules.
        """
        available = self._available()
        if available is None:
            return None
        size_classes = Counter(v.get("size_class", "unknown") for v in available)
        fuels = Counter(v.get("fuel", "unknown") for v in available)
        vehicles = []
        # Long-form text (directions, usage notes) stays out of state: the
        # recorder drops attributes over 16 kB. Full detail is one click
        # away via the check_availability service and device attributes.
        drop_keys = {"timeslots", "wayfinding", "instructions", "usage_information"}
        for vehicle in available:
            summary = {k: v for k, v in vehicle.items() if k not in drop_keys}
            slots = vehicle.get("timeslots")
            if isinstance(slots, list):
                summary["slot_count"] = len(slots)
                summary["free_slot_count"] = sum(1 for s in slots if isinstance(s, dict) and s.get("available"))
            vehicles.append(summary)
        return {
            "vehicles": vehicles,
            "by_size_class": dict(size_classes),
            "by_fuel": dict(fuels),
            "search_params": (self.coordinator.data or {}).get("search_params"),
        }
