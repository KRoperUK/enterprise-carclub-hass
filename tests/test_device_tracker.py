"""Tests for vehicle device trackers."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.enterprise_carclub.device_tracker import EnterpriseCarClubVehicleTracker

from .conftest import VEHICLE


def _tracker(entry, data, stack_id="53237"):
    coordinator = MagicMock()
    coordinator.data = data
    vehicle = dict(VEHICLE, stack_id=stack_id)
    return EnterpriseCarClubVehicleTracker(coordinator, entry, vehicle)


def test_tracker_reports_bay_location(mock_config_entry) -> None:
    """The tracker exposes the bay coordinates for the map."""
    tracker = _tracker(mock_config_entry, {"vehicles": [dict(VEHICLE, latitude=53.47, longitude=-2.29)]})
    assert tracker.latitude == 53.47
    assert tracker.longitude == -2.29
    assert tracker.unique_id.endswith("_stack_53237")


def test_tracker_unknown_when_absent(mock_config_entry) -> None:
    """A vehicle missing from the latest search has no location."""
    tracker = _tracker(mock_config_entry, {"vehicles": []})
    assert tracker.latitude is None
    assert tracker.longitude is None
    assert tracker.extra_state_attributes == {"stack_id": "53237", "present": False}


def test_tracker_attributes_for_booking(mock_config_entry) -> None:
    """Attributes carry what a booking decision needs."""
    tracker = _tracker(mock_config_entry, {"vehicles": [dict(VEHICLE)]})
    attributes = tracker.extra_state_attributes
    assert attributes is not None
    assert attributes["size_class"] == "small"
    assert attributes["availability"] == "good"


def test_tracker_exposes_preview_photo(mock_config_entry) -> None:
    """The tracker surfaces the vehicle thumbnail for the map view."""
    from .conftest import VEHICLE

    vehicle = dict(
        VEHICLE,
        thumb_url="https://booking.citycarclub.co.uk//images/client_images/vehicle_thumb_1.png",
    )
    tracker = _tracker(mock_config_entry, {"vehicles": [vehicle]})
    assert tracker.entity_picture == vehicle["thumb_url"]


def test_tracker_picture_missing_without_thumbnail(mock_config_entry) -> None:
    """No thumbnail means no picture, not a broken image."""
    tracker = _tracker(mock_config_entry, {"vehicles": [dict(VEHICLE)]})
    assert tracker.entity_picture is None


def test_tracker_without_data_has_no_location(mock_config_entry) -> None:
    """Missing coordinator data renders no location, not zeros."""
    tracker = _tracker(mock_config_entry, None)
    assert tracker.latitude is None
    assert tracker.longitude is None
    assert tracker.entity_picture is None


async def test_setup_only_tracks_favorites(hass, mock_config_entry) -> None:
    """Only favorite stacks get trackers; other search hits stay out of the device list."""
    from unittest.mock import MagicMock

    from custom_components.enterprise_carclub import device_tracker as tracker_module

    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(mock_config_entry, options={"favorite_stack_ids": ["53237"]})
    coordinator = MagicMock()
    coordinator.data = {"vehicles": [dict(VEHICLE, stack_id="53237"), dict(VEHICLE, stack_id="99999")]}
    mock_config_entry.runtime_data = coordinator

    added: list = []
    await tracker_module.async_setup_entry(hass, mock_config_entry, added.extend)
    await hass.async_block_till_done()
    assert [entity.unique_id for entity in added] == [f"{mock_config_entry.unique_id}_stack_53237"]


async def test_unfavorited_stale_devices_are_pruned(hass, mock_config_entry) -> None:
    """Removing a favorite deletes its orphaned device on next setup."""
    from unittest.mock import MagicMock

    from homeassistant.helpers import device_registry as dr

    from custom_components.enterprise_carclub import device_tracker as tracker_module
    from custom_components.enterprise_carclub.const import DOMAIN

    mock_config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    stale = registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "stack_99999")},
        name="Old favorite",
        manufacturer="Enterprise Car Club",
    )
    mock_config_entry.runtime_data = MagicMock()
    mock_config_entry.runtime_data.data = {"vehicles": []}

    await tracker_module.async_setup_entry(hass, mock_config_entry, lambda entities: None)
    await hass.async_block_till_done()
    assert registry.async_get(stale.id) is None
