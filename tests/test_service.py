"""Tests for the check_availability service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.enterprise_carclub.const import DOMAIN

COORDINATOR_CLIENT = "custom_components.enterprise_carclub.coordinator.Client"


async def test_check_availability_returns_future_slots(hass, mock_config_entry) -> None:
    """The service returns ISO timeslots for any future window."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.enterprise_carclub.coordinator.EnterpriseCarClubCoordinator._async_update_data",
            new=AsyncMock(return_value={"reservations": [], "messages": [], "vehicles": []}),
        ),
        patch(COORDINATOR_CLIENT) as mock_client_cls,
    ):
        client = mock_client_cls.return_value
        client.token = "tok"
        client.async_login = AsyncMock()
        client.async_get_stack_timeslots = AsyncMock(return_value=[{"time": 1795026600, "available": True}])
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        response = await hass.services.async_call(
            DOMAIN,
            "check_availability",
            {
                "stack_id": "53237",
                "start": datetime(2026, 11, 21, 18, 0, tzinfo=UTC),
                "end": datetime(2026, 11, 21, 21, 0, tzinfo=UTC),
            },
            blocking=True,
            return_response=True,
        )

    assert response is not None
    assert response["stack_id"] == "53237"
    assert response["timeslots"][0]["available"] is True
    assert response["timeslots"][0]["time"].startswith("2026-11-")
    _, kwargs = client.async_get_stack_timeslots.call_args
    assert kwargs["start_time"] < kwargs["end_time"]


async def test_book_vehicle_creates_reservation(hass, mock_config_entry) -> None:
    """The book service posts the window and returns the booking summary."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.enterprise_carclub.coordinator.EnterpriseCarClubCoordinator._async_update_data",
            new=AsyncMock(return_value={"reservations": [], "messages": [], "vehicles": []}),
        ),
        patch(COORDINATOR_CLIENT) as mock_client_cls,
    ):
        client = mock_client_cls.return_value
        client.token = "tok"
        client.async_login = AsyncMock()
        client.async_make_reservation = AsyncMock(
            return_value={
                "id": "14566233",
                "status": "normal",
                "estimate_unformatted": {"currency_amount": {"currency_code": "GBP", "value": 33.98}},
            }
        )
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        response = await hass.services.async_call(
            DOMAIN,
            "book_vehicle",
            {
                "stack_id": "54978",
                "start": datetime(2026, 11, 21, 18, 0, tzinfo=UTC),
                "end": datetime(2026, 11, 21, 22, 0, tzinfo=UTC),
                "memo": "test",
            },
            blocking=True,
            return_response=True,
        )

    assert response is not None
    assert response["reservation_id"] == "14566233"
    assert response["total"] == 33.98
    assert response["currency"] == "GBP"
    _, kwargs = client.async_make_reservation.call_args
    assert kwargs["memo"] == "test"


async def test_service_logs_in_when_token_missing(hass, mock_config_entry) -> None:
    """Services reuse the entry credentials when no token is cached."""
    mock_config_entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.enterprise_carclub.coordinator.EnterpriseCarClubCoordinator._async_update_data",
            new=AsyncMock(return_value={"reservations": [], "messages": [], "vehicles": []}),
        ),
        patch(COORDINATOR_CLIENT) as mock_client_cls,
    ):
        client = mock_client_cls.return_value
        client.token = None
        client.async_login = AsyncMock()
        client.async_get_stack_timeslots = AsyncMock(return_value=[])
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        await hass.services.async_call(
            DOMAIN,
            "check_availability",
            {"stack_id": "53237", "start": "2026-11-21T18:00:00+00:00", "end": "2026-11-21T19:00:00+00:00"},
            blocking=True,
            return_response=True,
        )

    client.async_login.assert_called_once()


async def test_service_without_setup_raises(hass) -> None:
    """Calling a service with no configured entry fails loudly."""
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.enterprise_carclub.services import async_setup_services

    async_setup_services(hass)
    async_setup_services(hass)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "check_availability",
            {"stack_id": "1", "start": "2026-11-21T18:00:00+00:00", "end": "2026-11-21T19:00:00+00:00"},
            blocking=True,
            return_response=True,
        )
