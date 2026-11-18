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
