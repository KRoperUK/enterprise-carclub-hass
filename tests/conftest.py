"""Fixtures for the Enterprise Car Club integration tests."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.enterprise_carclub.const import DOMAIN

USERNAME = "10379619"
PASSWORD = "secret"  # noqa: S105 — test-only credential

VEHICLE = {
    "stack_id": "53237",
    "description": "#53237: MediaCityUK M50 2EQ - Peugeot 208",
    "lot_description": "MediaCityUK M50 2EQ",
    "distance_m": 1221.6,
    "make_model": "Peugeot 208",
    "seats": 5,
    "fuel": "petrol",
    "transmission": "manual",
    "size_class": "small",
    "availability": "good",
    "next_free_time": "2026-11-18T20:00:00+00:00",
    "timeslots": [
        {"time": "2026-11-18T20:00:00+00:00", "available": True},
        {"time": "2026-11-18T20:15:00+00:00", "available": False},
    ],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> Any:
    """Load the custom integration in every test.

    Without this fixture Home Assistant refuses to set up anything under
    ``custom_components/`` and setup fails with "Integration not found".
    """
    yield


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a mock config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        options={},
        unique_id=USERNAME,
        title=f"Enterprise Car Club ({USERNAME})",
    )
