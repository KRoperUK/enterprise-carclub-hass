"""Tests for the Enterprise Car Club sensor platform."""

from __future__ import annotations

from custom_components.enterprise_carclub.sensor import (
    EnterpriseCarClubMessagesSensor,
    EnterpriseCarClubReservationsSensor,
)


def _build(sensor_cls, entry, data):
    coordinator = _coordinator(data)
    return sensor_cls(coordinator, entry)


def _coordinator(data):
    from unittest.mock import MagicMock

    coordinator = MagicMock()
    coordinator.data = data
    return coordinator


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
