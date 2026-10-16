"""Config flow for the Roth Touchline SL integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RothAuthError, RothConnectionError, RothTouchlineApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class RothTouchlineConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Roth Touchline SL."""

    VERSION = 1

    async def _async_login(
        self, username: str, password: str
    ) -> tuple[int | None, dict[str, str]]:
        """Try the credentials and return the user id or form errors."""
        api = RothTouchlineApi(async_get_clientsession(self.hass), username, password)
        try:
            return await api.login(), {}
        except RothAuthError:
            return None, {"base": "invalid_auth"}
        except RothConnectionError:
            return None, {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error logging in to Roth Touchline SL")
            return None, {"base": "unknown"}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the Roth account login."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id, errors = await self._async_login(
                user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if user_id is not None:
                await self.async_set_unique_id(str(user_id))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication when the stored login stops working."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the password again."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id, errors = await self._async_login(
                entry.data[CONF_USERNAME], user_input[CONF_PASSWORD]
            )
            if user_id is not None:
                await self.async_set_unique_id(str(user_id))
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )
