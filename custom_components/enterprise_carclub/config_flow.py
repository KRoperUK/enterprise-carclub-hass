"""Config flow and options flow for the enterprise_carclub integration."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from enterprise_carclub import AuthError, Client, ClientError

from .const import (
    CONF_CALENDAR_DAYS,
    CONF_FAVORITE_STACK_IDS,
    CONF_MARKET_ID,
    CONF_WINDOW_HOURS,
    DEFAULT_CALENDAR_DAYS,
    DEFAULT_MARKET_ID,
    DEFAULT_WINDOW_HOURS,
    DOMAIN,
    MAX_CALENDAR_DAYS,
)


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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return EnterpriseCarClubOptionsFlow(config_entry)

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle re-authentication when the stored password stops working."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            client = Client(async_get_clientsession(self.hass))
            try:
                await client.async_login(entry.data[CONF_USERNAME], password)
            except AuthError:
                errors["base"] = "invalid_auth"
            except ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 — surface unexpected failures as unknown
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(entry, data={**entry.data, CONF_PASSWORD: password})

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )


class EnterpriseCarClubOptionsFlow(OptionsFlow):
    """Handle options: search area, window, market and favorite vehicles."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize."""
        self._entry = entry

    def _favorite_choices(self) -> dict[str, str]:
        data = None
        runtime_data = getattr(self._entry, "runtime_data", None)
        if runtime_data is not None:
            data = getattr(runtime_data, "data", None)
        choices: dict[str, str] = {}
        if isinstance(data, dict):
            for vehicle in data.get("vehicles", []):
                if not isinstance(vehicle, dict):
                    continue
                stack_id = vehicle.get("stack_id")
                if isinstance(stack_id, str):
                    choices[stack_id] = str(vehicle.get("description") or stack_id)
        for stack_id in self._entry.options.get(CONF_FAVORITE_STACK_IDS, []):
            choices.setdefault(stack_id, stack_id)
        return choices

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        options = self._entry.options
        hass_config = self.hass.config
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_LATITUDE,
                        default=options.get(CONF_LATITUDE, hass_config.latitude),
                    ): cv.latitude,
                    vol.Optional(
                        CONF_LONGITUDE,
                        default=options.get(CONF_LONGITUDE, hass_config.longitude),
                    ): cv.longitude,
                    vol.Optional(
                        CONF_WINDOW_HOURS,
                        default=options.get(CONF_WINDOW_HOURS, DEFAULT_WINDOW_HOURS),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
                    vol.Optional(CONF_MARKET_ID, default=options.get(CONF_MARKET_ID, DEFAULT_MARKET_ID)): int,
                    vol.Optional(
                        CONF_CALENDAR_DAYS,
                        default=options.get(CONF_CALENDAR_DAYS, DEFAULT_CALENDAR_DAYS),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_CALENDAR_DAYS)),
                    vol.Optional(
                        CONF_FAVORITE_STACK_IDS,
                        default=options.get(CONF_FAVORITE_STACK_IDS, []),
                    ): cv.multi_select(self._favorite_choices()),
                }
            ),
            errors=errors,
        )
