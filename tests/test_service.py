"""Tests for the check_availability service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

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
