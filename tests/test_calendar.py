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
