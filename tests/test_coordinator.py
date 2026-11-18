"""Tests for the Enterprise Car Club coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from enterprise_carclub import AuthError, ClientError
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.enterprise_carclub.const import DEFAULT_SCAN_INTERVAL
from custom_components.enterprise_carclub.coordinator import EnterpriseCarClubCoordinator

COORDINATOR_CLIENT = "custom_components.enterprise_carclub.coordinator.Client"


async def test_update_data_returns_reservations_and_messages(hass, mock_config_entry) -> None:
    """Coordinator logs in once, then fetches reservations and messages."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = mock_client_cls.return_value
        client.token = None
        client.async_login = AsyncMock()
        client.async_get_current_and_future = AsyncMock(return_value=[{"id": "1"}])
        client.async_get_driver_messages = AsyncMock(return_value=[{"id": "3660"}])

        data = await coordinator._async_update_data()

    assert data["reservations"] == [{"id": "1"}]
    assert data["messages"] == [{"id": "3660"}]
    assert data["source"] == "cloud"
    client.async_login.assert_called_once()


async def test_auth_error_triggers_relogin(hass, mock_config_entry) -> None:
    """An expired token causes one re-login and a retry."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = mock_client_cls.return_value
        client.token = "stale"
        client.async_login = AsyncMock()
        client.async_get_current_and_future = AsyncMock(side_effect=[AuthError("expired"), [{"id": "2"}]])
        client.async_get_driver_messages = AsyncMock(return_value=[])

        data = await coordinator._async_update_data()

    assert data["reservations"] == [{"id": "2"}]
    client.async_login.assert_called_once()


async def test_bad_credentials_raise_config_entry_auth_failed(hass, mock_config_entry) -> None:
    """Repeated auth failure surfaces as ConfigEntryAuthFailed."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = mock_client_cls.return_value
        client.token = None
        client.async_login = AsyncMock(side_effect=AuthError("nope"))
        try:
            await coordinator._async_update_data()
        except ConfigEntryAuthFailed:
            return
        raise AssertionError("expected ConfigEntryAuthFailed")


async def test_api_failure_raises_update_failed(hass, mock_config_entry) -> None:
    """API outages surface as UpdateFailed."""
    coordinator = EnterpriseCarClubCoordinator(hass, mock_config_entry)

    with patch(COORDINATOR_CLIENT) as mock_client_cls:
        client = mock_client_cls.return_value
        client.token = "tok"
        client.async_login = AsyncMock()
        client.async_get_current_and_future = AsyncMock(side_effect=ClientError("down"))
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
