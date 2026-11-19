"""Tests for integration setup."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enterprise_carclub.const import DOMAIN

COORDINATOR_UPDATE = "custom_components.enterprise_carclub.coordinator.EnterpriseCarClubCoordinator._async_update_data"

PAYLOAD: dict[str, Any] = {
    "reservations": [{"id": "1"}],
    "messages": [{"id": "3660"}],
    "vehicles": [],
    "source": "cloud",
}


async def test_setup_and_unload(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Config entry sets up platforms and unloads cleanly."""
    mock_config_entry.add_to_hass(hass)

    # The patch must be an AsyncMock: the coordinator awaits this call, and a
    # plain MagicMock returning a dict would blow up with "can't await dict".
    with patch(COORDINATOR_UPDATE, new=AsyncMock(return_value=PAYLOAD)):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.domain == DOMAIN
        assert mock_config_entry.state is ConfigEntryState.LOADED

        sensor_ids = sorted(hass.states.async_entity_ids("sensor"))
        assert len(sensor_ids) == 3
        states = sorted(hass.states.get(eid).state for eid in sensor_ids)
        assert states == ["0", "1", "1"]

        assert hass.states.async_entity_ids("binary_sensor") == []
        assert hass.states.async_entity_ids("device_tracker") == []

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_forwards_the_coordinator_onto_the_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Setup stores the coordinator on entry.runtime_data for the platforms."""
    mock_config_entry.add_to_hass(hass)

    with patch(COORDINATOR_UPDATE, new=AsyncMock(return_value=PAYLOAD)):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    runtime_data: Any = mock_config_entry.runtime_data
    assert runtime_data is not None
    assert runtime_data.data == PAYLOAD
