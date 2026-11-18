"""Config flow for the enterprise_carclub integration."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from enterprise_carclub import AuthError, Client, ClientError

from .const import DOMAIN


class EnterpriseCarClubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Enterprise Car Club."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            password = user_input[CONF_PASSWORD]
            await self.async_set_unique_id(username)
            self._abort_if_unique_id_configured()
            client = Client(async_get_clientsession(self.hass))
            try:
                await client.async_login(username, password)
            except AuthError:
                errors["base"] = "invalid_auth"
            except ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 — surface unexpected failures as unknown
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"Enterprise Car Club ({username})",
                    data={CONF_USERNAME: username, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )
