"""Tests for the reservations calendar."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from custom_components.enterprise_carclub.calendar import (
    EnterpriseCarClubCalendar,
    _as_event,
)


def _reservation(**overrides: object) -> dict:
    payload: dict = {
        "id": "14566233",
        "status": "normal",
        "start_timestamp": 1795107600,
        "end_timestamp": 1795122000,
        "vehicle_stack": {
            "make_model": "Ford Transit Custom EV",
            "lot_description": "Blossom Street, Ancoats, M4 6AJ",
        },
        "estimate_unformatted": {"currency_amount": {"currency_code": "GBP", "value": 33.98}},
    }
    payload.update(overrides)
    return payload


def _calendar(entry, data) -> EnterpriseCarClubCalendar:
    coordinator = MagicMock()
    coordinator.data = data
    return EnterpriseCarClubCalendar(coordinator, entry)


def test_event_shape_from_reservation() -> None:
    """A reservation maps to a calendar event with summary and location."""
    event = _as_event(_reservation())
    assert event is not None
    assert event.uid == "14566233"
    assert "Ford Transit" in event.summary
    assert event.location == "Blossom Street, Ancoats, M4 6AJ"
    assert event.start.year == 2026


def test_event_skips_unparsable_reservations() -> None:
    """Reservations without epoch timestamps produce no event."""
    assert _as_event({"id": "x"}) is None


async def test_get_events_filters_by_range(hass, mock_config_entry) -> None:
    """Only overlapping reservations are returned for a range."""
    reservation = _reservation()
    calendar = _calendar(mock_config_entry, {"reservations": [reservation]})
    start = datetime.fromtimestamp(reservation["start_timestamp"], tz=UTC)
    end = datetime.fromtimestamp(reservation["end_timestamp"], tz=UTC)
    in_range = await calendar.async_get_events(
        hass,
        start.replace(hour=0, minute=0),
        end.replace(hour=23, minute=59),
    )
    assert len(in_range) == 1
    out_of_range = await calendar.async_get_events(
        hass,
        datetime(2026, 11, 23, 18, 0, tzinfo=UTC),
        datetime(2026, 11, 23, 22, 0, tzinfo=UTC),
    )
    assert out_of_range == []


async def test_malformed_timestamps_produce_no_events(hass, mock_config_entry) -> None:
    """Reservations with non-epoch timestamps are skipped, not crashed on."""
    calendar = _calendar(mock_config_entry, {"reservations": [{"id": "x", "start_timestamp": "soon"}]})
    assert calendar.event is None
    assert (
        await calendar.async_get_events(
            hass,
            datetime(2026, 11, 21, tzinfo=UTC),
            datetime(2026, 11, 22, tzinfo=UTC),
        )
        == []
    )


async def test_event_property_returns_next_upcoming(hass, mock_config_entry) -> None:
    """The entity event is the soonest reservation still in progress."""
    past = _reservation(id="old", start_timestamp=1700000000, end_timestamp=1700003600)
    calendar = _calendar(mock_config_entry, {"reservations": [past, _reservation()]})
    assert calendar.event is not None
    assert calendar.event.uid == "14566233"


async def test_no_data_means_no_event(hass, mock_config_entry) -> None:
    """Missing coordinator data renders no event rather than erroring."""
    calendar = _calendar(mock_config_entry, None)
    assert calendar.event is None
    assert (
        await calendar.async_get_events(
            hass,
            datetime(2026, 11, 21, tzinfo=UTC),
            datetime(2026, 11, 22, tzinfo=UTC),
        )
        == []
    )


def _avail_entry(stack_id: str = "53237") -> dict:
    from .conftest import VEHICLE

    return {"vehicles": [dict(VEHICLE, stack_id=stack_id)]}


def _avail_calendar(entry, data, stack_id="53237"):
    from unittest.mock import MagicMock

    from custom_components.enterprise_carclub.calendar import EnterpriseCarClubAvailabilityCalendar

    coordinator = MagicMock()
    coordinator.data = data
    return EnterpriseCarClubAvailabilityCalendar(coordinator, entry, stack_id)


def test_merge_slots_groups_consecutive_windows() -> None:
    """Adjacent free slots merge; gaps and busy slots split windows."""
    from custom_components.enterprise_carclub.calendar import _merge_slots

    base = datetime(2026, 11, 21, 18, 0, tzinfo=UTC).timestamp()
    slots = [
        {"time": datetime.fromtimestamp(base, tz=UTC).isoformat(), "available": True},
        {"time": datetime.fromtimestamp(base + 900, tz=UTC).isoformat(), "available": True},
        {"time": datetime.fromtimestamp(base + 1800, tz=UTC).isoformat(), "available": False},
        {"time": datetime.fromtimestamp(base + 2700, tz=UTC).isoformat(), "available": True},
        {"time": "not-a-time", "available": True},
        {"available": True},
    ]
    windows = _merge_slots(slots)
    assert windows == [(int(base), int(base) + 1800), (int(base) + 2700, int(base) + 3600)]


async def test_availability_calendar_shows_free_windows(hass, mock_config_entry) -> None:
    """A favorite's free windows appear as calendar events."""
    import time

    from .conftest import VEHICLE

    base = int(time.time() // 900 * 900) + 3600
    slots = [
        {"time": datetime.fromtimestamp(base, tz=UTC).isoformat(), "available": True},
        {"time": datetime.fromtimestamp(base + 900, tz=UTC).isoformat(), "available": True},
    ]
    calendar = _avail_calendar(mock_config_entry, {"vehicles": [dict(VEHICLE, stack_id="53237", timeslots=slots)]})
    assert "53237" in (calendar.name or "")
    assert calendar.event is not None
    assert calendar.event.summary.endswith("available")
    events = await calendar.async_get_events(
        hass,
        datetime.fromtimestamp(base - 3600, tz=UTC),
        datetime.fromtimestamp(base + 7200, tz=UTC),
    )
    assert len(events) == 1
    assert events[0].uid.startswith("53237-")


async def test_availability_calendar_empty_without_vehicle(hass, mock_config_entry) -> None:
    """No vehicle data means no windows and a fallback name."""
    calendar = _avail_calendar(mock_config_entry, {"vehicles": []})
    assert calendar.event is None
    assert calendar.name == "Availability (53237)"
    assert (
        await calendar.async_get_events(
            hass,
            datetime(2026, 11, 21, tzinfo=UTC),
            datetime(2026, 11, 22, tzinfo=UTC),
        )
        == []
    )


async def test_availability_calendars_created_per_favorite(hass, mock_config_entry) -> None:
    """Setup adds one availability calendar per favorite stack."""
    from unittest.mock import MagicMock

    from custom_components.enterprise_carclub import calendar as calendar_module

    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={"favorite_stack_ids": ["9", "8"]})
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = {"vehicles": []}

    added: list = []
    await calendar_module.async_setup_entry(hass, mock_config_entry, added.extend)
    await hass.async_block_till_done()
    kinds = sorted(type(entity).__name__ for entity in added)
    assert kinds == [
        "EnterpriseCarClubAvailabilityCalendar",
        "EnterpriseCarClubAvailabilityCalendar",
        "EnterpriseCarClubCalendar",
    ]
