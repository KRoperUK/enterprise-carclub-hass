"""Tests for the Enterprise Car Club options flow."""

from __future__ import annotations

from homeassistant.data_entry_flow import FlowResultType


async def _start_options(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    return await hass.config_entries.options.async_init(mock_config_entry.entry_id)


async def test_options_form_defaults(hass, mock_config_entry) -> None:
    """The options form renders with current values prefilled."""
    result = await _start_options(hass, mock_config_entry)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_save_creates_entry(hass, mock_config_entry) -> None:
    """Saving options stores search area, window and favorites."""
    from unittest.mock import MagicMock

    from .conftest import VEHICLE

    coordinator = MagicMock()
    coordinator.data = {"vehicles": [dict(VEHICLE)]}
    mock_config_entry.runtime_data = coordinator
    result = await _start_options(hass, mock_config_entry)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "latitude": 53.47,
            "longitude": -2.29,
            "window_hours": 6,
            "market_id": 8,
            "favorite_stack_ids": ["53237"],
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["favorite_stack_ids"] == ["53237"]
    assert result["data"]["window_hours"] == 6
