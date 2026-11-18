"""Tests for the Enterprise Car Club config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from enterprise_carclub import AuthError, ClientError, LoginResult
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType

from custom_components.enterprise_carclub.const import DOMAIN

from .conftest import PASSWORD, USERNAME

FLOW_CLIENT = "custom_components.enterprise_carclub.config_flow.Client"


def _login_result() -> LoginResult:
    return LoginResult(
        authorization_token="tok",
        member_id=USERNAME,
        driver_name="Test Driver",
        market_id=8,
    )


async def _start(hass):
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})


async def test_form_is_shown(hass) -> None:
    """The user step renders an empty form."""
    result = await _start(hass)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_valid_credentials_create_the_entry(hass) -> None:
    """Valid credentials validate against the API and create the entry."""
    result = await _start(hass)

    with patch(FLOW_CLIENT) as mock_client_cls:
        mock_client_cls.return_value.async_login = AsyncMock(return_value=_login_result())
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Enterprise Car Club ({USERNAME})"
    assert result["data"] == {CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD}


async def test_invalid_auth_shows_error(hass) -> None:
    """Bad credentials surface invalid_auth without creating an entry."""
    result = await _start(hass)

    with patch(FLOW_CLIENT) as mock_client_cls:
        mock_client_cls.return_value.async_login = AsyncMock(side_effect=AuthError("nope"))
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: "wrong"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_connection_failure_shows_error(hass) -> None:
    """API outages surface cannot_connect without creating an entry."""
    result = await _start(hass)

    with patch(FLOW_CLIENT) as mock_client_cls:
        mock_client_cls.return_value.async_login = AsyncMock(side_effect=ClientError("down"))
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_username_aborts(hass, mock_config_entry) -> None:
    """A second entry for the same member aborts."""
    mock_config_entry.add_to_hass(hass)
    result = await _start(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
