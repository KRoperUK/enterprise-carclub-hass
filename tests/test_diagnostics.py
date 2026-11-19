"""Tests for diagnostics redaction."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.enterprise_carclub.const import DOMAIN

COORDINATOR_UPDATE = "custom_components.enterprise_carclub.coordinator.EnterpriseCarClubCoordinator._async_update_data"


def _coordinator_with(data: Any) -> MagicMock:
    coordinator = MagicMock()
    coordinator.data = data
    return coordinator


async def test_diagnostics_redacts_credentials_and_tokens(hass, mock_config_entry) -> None:
    """Passwords and tokens never appear in diagnostics output."""
    from custom_components.enterprise_carclub import diagnostics as diagnostics_module

    mock_config_entry.add_to_hass(hass)
    payload = {
        "reservations": [],
        "messages": [],
        "vehicles": [],
        "authorization_token": "tok-should-not-appear",
    }
    with patch(COORDINATOR_UPDATE, new=AsyncMock(return_value=payload)):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    result = await diagnostics_module.async_get_config_entry_diagnostics(hass, mock_config_entry)
    dumped = str(result)
    assert "tok-should-not-appear" not in dumped
    assert "secret" not in dumped
    assert result["entry"]["username"] == "10379619"
    assert result["data"]["reservations"] == []


def test_redact_handles_scalars_and_lists() -> None:
    """The redactor preserves structure while masking secrets."""
    from custom_components.enterprise_carclub.diagnostics import _redacted

    assert _redacted("plain") == "plain"
    assert _redacted(42) == 42
    assert _redacted([{"authorization_token": "tok"}, "ok"]) == [
        {"authorization_token": "**REDACTED**"},
        "ok",
    ]
