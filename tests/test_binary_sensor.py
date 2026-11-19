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


def test_friendly_name_uses_model_and_stack_id(mock_config_entry) -> None:
    """The friendly name reads like ``Peugeot 208 (#53237)``."""
    sensor = _build(
        mock_config_entry,
        {"vehicles": [dict(VEHICLE, make_model="Peugeot 208", lot_description="MediaCityUK M50 2EQ")]},
    )
    assert sensor.name == "Peugeot 208, MediaCityUK M50 2EQ (53237)"


def test_friendly_name_falls_back_without_vehicle(mock_config_entry) -> None:
    """Without search data the name falls back to the stack id."""
    sensor = _build(mock_config_entry, None)
    assert sensor.name == "Favorite 53237"


def test_display_name_without_location(mock_config_entry) -> None:
    """A vehicle without location details still names the model."""
    from custom_components.enterprise_carclub.binary_sensor import vehicle_display_name

    assert vehicle_display_name({"make_model": "Peugeot 208"}, "1") == "Peugeot 208 (1)"
    assert vehicle_display_name({}, "2") == "Favorite 2"


async def test_setup_creates_one_entity_per_favorite(hass, mock_config_entry) -> None:
    """Setup adds a binary sensor for each favorite stack id."""
    from custom_components.enterprise_carclub import binary_sensor as binary_sensor_module

    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={"favorite_stack_ids": ["53237", "54978"]})
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = {"vehicles": []}
    added: list = []

    def capture(entities: list) -> None:
        added.extend(entities)

    await binary_sensor_module.async_setup_entry(hass, mock_config_entry, capture)
    assert len(added) == 2
    assert {entity.unique_id for entity in added} == {
        f"{mock_config_entry.unique_id}_fav_53237",
        f"{mock_config_entry.unique_id}_fav_54978",
    }
