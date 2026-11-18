"""Tests for the Enterprise Car Club sensor platform."""

from __future__ import annotations

from custom_components.enterprise_carclub.sensor import (
    EnterpriseCarClubAvailableVehiclesSensor,
    EnterpriseCarClubMessagesSensor,
    EnterpriseCarClubReservationsSensor,
)

from .conftest import VEHICLE


def _build(sensor_cls, entry, data):
    from unittest.mock import MagicMock

    coordinator = MagicMock()
    coordinator.data = data
    return sensor_cls(coordinator, entry)


def test_reservations_sensor_reports_count(mock_config_entry) -> None:
    """The reservations sensor counts upcoming reservations."""
    sensor = _build(
        EnterpriseCarClubReservationsSensor,
        mock_config_entry,
        {"reservations": [{"id": "1"}, {"id": "2"}], "messages": []},
    )
    assert sensor.native_value == 2
    assert sensor.unique_id.endswith("_reservations")


def test_messages_sensor_reports_count(mock_config_entry) -> None:
    """The messages sensor counts driver inbox messages."""
    sensor = _build(
        EnterpriseCarClubMessagesSensor,
        mock_config_entry,
        {"reservations": [], "messages": [{"id": "3660"}]},
    )
    assert sensor.native_value == 1
    assert sensor.unique_id.endswith("_messages")


def test_available_vehicles_sensor_counts_good_only(mock_config_entry) -> None:
    """Only stacks with good availability are counted."""
    vehicles = [
        dict(VEHICLE),
        dict(VEHICLE, stack_id="other", availability="limited"),
    ]
    sensor = _build(
        EnterpriseCarClubAvailableVehiclesSensor,
        mock_config_entry,
        {"reservations": [], "messages": [], "vehicles": vehicles},
    )
    assert sensor.native_value == 1
    assert sensor.unique_id.endswith("_vehicles")
    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert attributes["by_size_class"] == {"small": 1}
    assert attributes["by_fuel"] == {"petrol": 1}
    assert len(attributes["vehicles"]) == 1
    assert "timeslots" not in attributes["vehicles"][0]
    assert attributes["vehicles"][0]["slot_count"] == 2
    assert attributes["vehicles"][0]["free_slot_count"] == 1


def test_unique_id_and_device_info(mock_config_entry) -> None:
    """Sensors share one device rooted at the config entry."""
    sensor = _build(
        EnterpriseCarClubReservationsSensor,
        mock_config_entry,
        {"reservations": [], "messages": []},
    )
    assert sensor.device_info is not None
    assert sensor.device_info["manufacturer"] == "Enterprise Car Club"
    assert sensor.device_info["name"] == mock_config_entry.title


def test_no_data_returns_none(mock_config_entry) -> None:
    """Missing coordinator data renders as unknown, not zero."""
    sensor = _build(EnterpriseCarClubReservationsSensor, mock_config_entry, None)
    assert sensor.native_value is None
