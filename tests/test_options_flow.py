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


async def test_options_preserves_saved_favorites_without_search_data(hass, mock_config_entry) -> None:
    """Saved favorites stay selectable even before any search ran."""
    from unittest.mock import MagicMock

    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={"favorite_stack_ids": ["99999"]})
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = None
    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    schema = result["data_schema"].schema
    key = next(k for k in schema if str(k) == "favorite_stack_ids")
    assert schema[key].options == {"99999": "99999"}


async def test_options_ignores_malformed_vehicles(hass, mock_config_entry) -> None:
    """Non-dict vehicle payloads never reach the favorites list."""
    from unittest.mock import MagicMock

    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = {"vehicles": ["oops", {"stack_id": 42}]}
    result = await _start_options(hass, mock_config_entry)

    schema = result["data_schema"].schema
    key = next(k for k in schema if str(k) == "favorite_stack_ids")
    assert schema[key].options == {}
