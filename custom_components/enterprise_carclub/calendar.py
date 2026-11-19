"""Calendar platform exposing Enterprise Car Club reservations as events."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .binary_sensor import vehicle_display_name
from .const import CONF_FAVORITE_STACK_IDS, DOMAIN
from .coordinator import EnterpriseCarClubCoordinator

PARALLEL_UPDATES = 1


def _as_timestamp(value: date | datetime) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    return datetime(value.year, value.month, value.day, tzinfo=UTC).timestamp()


def _merge_slots(slots: list[dict[str, Any]]) -> list[tuple[int, int]]:
    """Merge consecutive available 15-minute slots into (start, end) windows.

    Slot times are ISO-8601 strings (see coordinator); entries that do not
    parse are skipped.
    """
    times: list[int] = []
    for slot in slots:
        if not isinstance(slot, dict) or slot.get("available") is not True:
            continue
        raw = slot.get("time")
        try:
            stamp = datetime.fromisoformat(str(raw)).timestamp()
        except TypeError, ValueError:
            continue
        times.append(int(stamp))
    times.sort()
    windows: list[tuple[int, int]] = []
    for stamp in times:
        if windows and stamp <= windows[-1][1] + 60:
            windows[-1] = (windows[-1][0], stamp + 900)
        else:
            windows.append((stamp, stamp + 900))
    return windows


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the reservations calendar plus one availability calendar per favorite."""
    coordinator: EnterpriseCarClubCoordinator = entry.runtime_data
    favorites = entry.options.get(CONF_FAVORITE_STACK_IDS, [])
    async_add_entities(
        [EnterpriseCarClubCalendar(coordinator, entry)]
        + [
            EnterpriseCarClubAvailabilityCalendar(coordinator, entry, stack_id)
            for stack_id in favorites
            if isinstance(stack_id, str)
        ]
    )


def _as_utc(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, tz=UTC)


def _as_event(reservation: dict[str, Any]) -> CalendarEvent | None:
    start = reservation.get("start_timestamp")
    end = reservation.get("end_timestamp")
    if not isinstance(start, int) or not isinstance(end, int):
        return None
    stack = reservation.get("vehicle_stack")
    stack_dict = stack if isinstance(stack, dict) else {}
    make_model = stack_dict.get("make_model") or "Vehicle"
    lot = stack_dict.get("lot_description") or ""
    summary = f"{make_model}, {lot}".strip().rstrip(",")
    description_lines = [f"Reservation {reservation.get('id')} ({reservation.get('status')})"]
    estimate = reservation.get("estimate_unformatted")
    if isinstance(estimate, dict):
        amount = estimate.get("currency_amount")
        if isinstance(amount, dict) and isinstance(amount.get("value"), (int, float)):
            description_lines.append(f"Estimate: {amount.get('value')} {amount.get('currency_code', '')}".strip())
    return CalendarEvent(
        uid=str(reservation.get("id")),
        summary=summary or "Enterprise Car Club reservation",
        description="\n".join(description_lines),
        start=_as_utc(start),
        end=_as_utc(end),
        location=lot if isinstance(lot, str) else None,
    )


class EnterpriseCarClubCalendar(CoordinatorEntity[EnterpriseCarClubCoordinator], CalendarEntity):
    """Reservations as calendar events for automations and the HA calendar."""

    _attr_has_entity_name = True
    _attr_translation_key = "reservations"

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_calendar"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id or entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Enterprise Car Club",
        }

    def _reservations(self) -> list[dict[str, Any]]:
        data = self.coordinator.data
        if not data:
            return []
        items = data.get("reservations")
        return [r for r in items if isinstance(r, dict)] if isinstance(items, list) else []

    @staticmethod
    def _reservation_start(reservation: dict[str, Any]) -> int:
        start = reservation.get("start_timestamp")
        return start if isinstance(start, int) else 0

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming reservation, if any."""
        now = datetime.now(tz=UTC).timestamp()
        upcoming = [
            r for r in self._reservations() if isinstance(r.get("end_timestamp"), int) and r["end_timestamp"] > now
        ]
        upcoming.sort(key=EnterpriseCarClubCalendar._reservation_start)
        return _as_event(upcoming[0]) if upcoming else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return reservations overlapping the requested range."""
        start_ts = start_date.timestamp()
        end_ts = end_date.timestamp()
        events = []
        for reservation in self._reservations():
            res_start = reservation.get("start_timestamp")
            res_end = reservation.get("end_timestamp")
            if not isinstance(res_start, int) or not isinstance(res_end, int):
                continue
            if res_end < start_ts or res_start > end_ts:
                continue
            event = _as_event(reservation)
            if event is not None:
                events.append(event)
        return events


class EnterpriseCarClubAvailabilityCalendar(CoordinatorEntity[EnterpriseCarClubCoordinator], CalendarEntity):
    """Free windows of one favorite vehicle, as calendar events."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EnterpriseCarClubCoordinator, entry: ConfigEntry, stack_id: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._stack_id = stack_id
        self._attr_unique_id = f"{entry.unique_id}_avail_{stack_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"stack_{stack_id}")},
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

    def _windows(self) -> list[CalendarEvent]:
        vehicle = self._vehicle()
        if not vehicle:
            return []
        slots = vehicle.get("timeslots")
        if not isinstance(slots, list):
            return []
        name = vehicle_display_name(vehicle, self._stack_id)
        events = []
        for start_ts, end_ts in _merge_slots(slots):
            events.append(
                CalendarEvent(
                    uid=f"{self._stack_id}-{start_ts}",
                    summary=f"{name} available",
                    description=f"Bookable window for {name}",
                    start=datetime.fromtimestamp(start_ts, tz=UTC),
                    end=datetime.fromtimestamp(end_ts, tz=UTC),
                )
            )
        return events

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming free window, if any."""
        now = datetime.now(tz=UTC).timestamp()
        upcoming = [e for e in self._windows() if _as_timestamp(e.end) > now]
        return upcoming[0] if upcoming else None

    @property
    def name(self) -> str | None:
        """Name follows the vehicle so each favorite is distinguishable."""
        vehicle = self._vehicle()
        if vehicle is None:
            return f"Availability ({self._stack_id})"
        return f"{vehicle_display_name(vehicle, self._stack_id)} availability"

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return free windows overlapping the requested range."""
        start_ts = start_date.timestamp()
        end_ts = end_date.timestamp()
        return [
            event
            for event in self._windows()
            if _as_timestamp(event.end) >= start_ts and _as_timestamp(event.start) <= end_ts
        ]
