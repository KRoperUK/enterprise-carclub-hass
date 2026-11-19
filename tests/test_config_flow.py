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


async def test_reauth_updates_password(hass, mock_config_entry) -> None:
    """Re-auth validates the new password and updates the entry."""
    from enterprise_carclub import LoginResult

    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": mock_config_entry.entry_id}
    )
    assert result["type"] == FlowResultType.FORM

    with patch(FLOW_CLIENT) as mock_client_cls:
        mock_client_cls.return_value.async_login = AsyncMock(
            return_value=LoginResult(authorization_token="new-tok", member_id=USERNAME, driver_name="T", market_id=8)
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_PASSWORD: "new-secret"},
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_PASSWORD] == "new-secret"


async def test_unexpected_error_surfaces_unknown(hass) -> None:
    """Unexpected API failures surface as unknown, not a crash."""
    result = await _start(hass)

    with patch(FLOW_CLIENT) as mock_client_cls:
        mock_client_cls.return_value.async_login = AsyncMock(side_effect=RuntimeError("boom"))
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_USERNAME: USERNAME, CONF_PASSWORD: PASSWORD},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_reauth_connection_failure_stays_on_form(hass, mock_config_entry) -> None:
    """Re-auth maps connectivity and unexpected failures distinctly."""
    mock_config_entry.add_to_hass(hass)
    for side_effect, expected in ((ClientError("down"), "cannot_connect"), (RuntimeError("boom"), "unknown")):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "reauth", "entry_id": mock_config_entry.entry_id}
        )
        with patch(FLOW_CLIENT) as mock_client_cls:
            mock_client_cls.return_value.async_login = AsyncMock(side_effect=side_effect)
            result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_PASSWORD: "x"})
        assert result["errors"] == {"base": expected}


async def test_reauth_invalid_password_stays_on_form(hass, mock_config_entry) -> None:
    """A wrong replacement password keeps the reauth form open."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": mock_config_entry.entry_id}
    )
    with patch(FLOW_CLIENT) as mock_client_cls:
        mock_client_cls.return_value.async_login = AsyncMock(side_effect=AuthError("nope"))
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input={CONF_PASSWORD: "wrong"})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
