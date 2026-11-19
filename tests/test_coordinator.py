"""Tests for the Enterprise Car Club coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from enterprise_carclub import AuthError, ClientError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.enterprise_carclub.const import DEFAULT_SCAN_INTERVAL
from custom_components.enterprise_carclub.coordinator import EnterpriseCarClubCoordinator

COORDINATOR_CLIENT = "custom_components.enterprise_carclub.coordinator.Client"


def _search_entry() -> dict:
    return {
        "availability": "good",
        "distance": 1221.6,
        "timeslots": [{"time": 1795026600, "available": True}],
        "vehicle_stack": {
            "id": "53237",
            "description": "#53237: Peugeot 208",
            "latitude": 53.47,
            "longitude": -2.29,
            "make_model": "Peugeot 208",
            "vehicle_details": {"plate": "FL26 PKZ", "year": 2026},
        },
    }


def _mock_client():
    client = AsyncMock()
    client.token = None
    client.async_login = AsyncMock()
    client.async_get_current_and_future = AsyncMock(return_value=[])
    client.async_get_driver_messages = AsyncMock(return_value=[])
    client.async_search_stacks = AsyncMock(return_value=[_search_entry()])
    return client


async def test_update_data_returns_reservations_messages_and_vehicles(hass, mock_config_entry) -> None:
    """Coordinator logs in once, then fetches reservations, messages and search."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        mock_client_cls.return_value = _mock_client()
        data = await coordinator._async_update_data()

    assert data["reservations"] == []
    assert data["messages"] == []
    assert len(data["vehicles"]) == 1
    assert data["vehicles"][0]["stack_id"] == "53237"
    assert data["vehicles"][0]["size_class"] == "small"
    assert data["source"] == "cloud"


async def test_vehicles_link_to_matching_reservations(hass, mock_config_entry) -> None:
    """A vehicle with a future booking carries the reservation summary."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)
    reservation = {
        "id": "14566233",
        "status": "normal",
        "start_timestamp": 1795107600,
        "end_timestamp": 1795122000,
        "vehicle_stack": {"id": "53237"},
    }

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = _mock_client()
        client.async_get_current_and_future = AsyncMock(return_value=[reservation])
        mock_client_cls.return_value = client
        data = await coordinator._async_update_data()

    assert data["vehicles"][0]["reservation"]["id"] == "14566233"
    assert data["vehicles"][0]["reservation"]["start"].startswith("2026-")


async def test_auth_error_triggers_relogin(hass, mock_config_entry) -> None:
    """An expired token causes one re-login and a retry."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = _mock_client()
        client.token = "stale"
        client.async_get_current_and_future = AsyncMock(side_effect=[AuthError("expired"), [{"id": "2"}]])
        mock_client_cls.return_value = client
        data = await coordinator._async_update_data()

    assert data["reservations"] == [{"id": "2"}]
    client.async_login.assert_called_once()


async def test_non_dict_stacks_are_skipped(hass, mock_config_entry) -> None:
    """Malformed stack entries never reach entity attributes."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = _mock_client()
        client.async_search_stacks = AsyncMock(return_value=["oops", 42])
        mock_client_cls.return_value = client
        data = await coordinator._async_update_data()

    assert data["vehicles"] == []


async def test_bad_credentials_raise_config_entry_auth_failed(hass, mock_config_entry) -> None:
    """Repeated auth failure surfaces as ConfigEntryAuthFailed."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = _mock_client()
        client.async_login = AsyncMock(side_effect=AuthError("nope"))
        mock_client_cls.return_value = client
        try:
            await coordinator._async_update_data()
        except ConfigEntryAuthFailed:
            return
        raise AssertionError("expected ConfigEntryAuthFailed")


async def test_api_failure_raises_update_failed(hass, mock_config_entry) -> None:
    """API outages surface as UpdateFailed."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = _mock_client()
        client.token = "tok"
        client.async_get_current_and_future = AsyncMock(side_effect=ClientError("down"))
        mock_client_cls.return_value = client
        try:
            await coordinator._async_update_data()
        except UpdateFailed:
            return
        raise AssertionError("expected UpdateFailed")


def test_scan_interval_comes_from_constants(hass, mock_config_entry) -> None:
    """The poll interval is driven by DEFAULT_SCAN_INTERVAL."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    assert coordinator.update_interval is not None
    assert coordinator.update_interval.total_seconds() == DEFAULT_SCAN_INTERVAL
    assert coordinator.entry is mock_config_entry
