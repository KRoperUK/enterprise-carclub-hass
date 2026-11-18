"""Tests for favorite-vehicle binary sensors."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.enterprise_carclub.binary_sensor import (
    EnterpriseCarClubFavoriteAvailableSensor,
)

from .conftest import VEHICLE


def _build(entry, data, stack_id="53237"):
    coordinator = MagicMock()
    coordinator.data = data
    return EnterpriseCarClubFavoriteAvailableSensor(coordinator, entry, stack_id)


def test_favorite_on_when_availability_good(mock_config_entry) -> None:
    """A favorite in the search with good availability reads on."""
    sensor = _build(mock_config_entry, {"vehicles": [dict(VEHICLE)]})
    assert sensor.is_on is True
    assert sensor.unique_id.endswith("_fav_53237")
    assert sensor.extra_state_attributes is not None
    assert sensor.extra_state_attributes["present"] is True


def test_favorite_off_when_availability_poor(mock_config_entry) -> None:
    """A favorite with poor availability reads off."""
    sensor = _build(mock_config_entry, {"vehicles": [dict(VEHICLE, availability="limited")]})
    assert sensor.is_on is False


def test_favorite_unknown_when_absent_from_search(mock_config_entry) -> None:
    """A favorite missing from the latest search reads unknown."""
    sensor = _build(mock_config_entry, {"vehicles": []})
    assert sensor.is_on is None
    assert sensor.extra_state_attributes == {"stack_id": "53237", "present": False}
