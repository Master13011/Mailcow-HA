"""Config flow for the Mailcow integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import MailcowAPI, normalize_base_url
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .exceptions import (
    MailcowAPIError,
    MailcowAuthenticationError,
    MailcowConnectionError,
    MailcowInvalidURLError,
    MailcowSSLError,
)
from .options_flow import MailcowOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)

_API_KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): TextSelector(
            TextSelectorConfig(type=TextSelectorType.URL)
        ),
        vol.Required(CONF_API_KEY): _API_KEY_SELECTOR,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
        vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=False): bool,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
            NumberSelectorConfig(
                min=1,
                max=1440,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="min",
            )
        ),
    }
)

STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): _API_KEY_SELECTOR})

STEP_RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): _API_KEY_SELECTOR,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


class MailcowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mailcow."""

    VERSION = 2

    async def _async_validate(
        self, base_url: str, api_key: str, verify_ssl: bool
    ) -> str | None:
        """Try the credentials. Return an error key, or None if everything is fine."""
        session = async_get_clientsession(self.hass, verify_ssl=verify_ssl)
        api = MailcowAPI({CONF_BASE_URL: base_url, CONF_API_KEY: api_key}, session)
        try:
            version = await api.get_status_version()
        except MailcowAuthenticationError:
            return "invalid_auth"
        except MailcowSSLError:
            return "ssl_error"
        except MailcowConnectionError:
            return "cannot_connect"
        except MailcowAPIError:
            return "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error during Mailcow validation")
            return "unknown"
        return None if version else "cannot_connect"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                base_url = normalize_base_url(user_input[CONF_BASE_URL])
            except MailcowInvalidURLError:
                errors["base"] = "invalid_url"
            else:
                await self.async_set_unique_id(base_url.lower())
                self._abort_if_unique_id_configured()
                verify_ssl = user_input[CONF_VERIFY_SSL]
                error = await self._async_validate(
                    base_url, user_input[CONF_API_KEY], verify_ssl
                )
                if error is None:
                    return self.async_create_entry(
                        title="Mailcow",
                        data={
                            CONF_BASE_URL: base_url,
                            CONF_API_KEY: user_input[CONF_API_KEY],
                            CONF_VERIFY_SSL: verify_ssl,
                        },
                        options={
                            CONF_DISABLE_CHECK_AT_NIGHT: user_input.get(
                                CONF_DISABLE_CHECK_AT_NIGHT, False
                            ),
                            CONF_SCAN_INTERVAL: int(
                                user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                            ),
                        },
                    )
                errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication (invalid or revoked API key)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API key."""
        return await self._async_credentials_step("reauth_confirm", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the API key / TLS verification of an existing entry."""
        return await self._async_credentials_step("reconfigure", user_input)

    async def _async_credentials_step(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        entry = (
            self._get_reauth_entry()
            if self.source == SOURCE_REAUTH
            else self._get_reconfigure_entry()
        )
        errors: dict[str, str] = {}

        if user_input is not None:
            verify_ssl = user_input.get(
                CONF_VERIFY_SSL, entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
            )
            error = await self._async_validate(
                entry.data[CONF_BASE_URL], user_input[CONF_API_KEY], verify_ssl
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_VERIFY_SSL: verify_ssl,
                    },
                )
            errors["base"] = error

        schema = STEP_REAUTH_SCHEMA if step_id == "reauth_confirm" else STEP_RECONFIGURE_SCHEMA
        suggested = {CONF_VERIFY_SSL: entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)}
        return self.async_show_form(
            step_id=step_id,
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
            description_placeholders={"base_url": entry.data[CONF_BASE_URL]},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> MailcowOptionsFlowHandler:
        """Return the options flow."""
        return MailcowOptionsFlowHandler()
