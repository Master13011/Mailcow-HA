import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
)
from .api import MailcowAPI
from .exceptions import (
    MailcowAuthenticationError,
    MailcowConnectionError,
    MailcowAPIError,
)
from typing import Dict

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class AuthenticationError(HomeAssistantError):
    """Error to indicate authentication failure."""


class MailcowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: Dict[str, str] = {}
        if user_input is not None:
            try:
                await self._validate_input(user_input)
                return self.async_create_entry(
                    title="Mailcow",
                    data={
                        CONF_BASE_URL: user_input[CONF_BASE_URL],
                    },
                    options={
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_DISABLE_CHECK_AT_NIGHT: user_input.get(CONF_DISABLE_CHECK_AT_NIGHT, False),
                        CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 10),
                    },
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.exception("Unexpected exception: %s", e)
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_BASE_URL): str,
            vol.Required(CONF_API_KEY): str,
            vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=False): bool,
            vol.Optional(CONF_SCAN_INTERVAL, default=10): vol.All(int, vol.Range(min=1)),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _validate_input(self, user_input: dict) -> None:
        session = async_get_clientsession(self.hass)
        api = MailcowAPI(user_input, session)
        try:
            version = await api.get_status_version()
            if not version:
                raise CannotConnect("No version received")
        except MailcowAuthenticationError as err:
            raise AuthenticationError from err
        except MailcowConnectionError as err:
            raise CannotConnect from err
        except MailcowAPIError as err:
            raise CannotConnect from err
        except Exception as err:
            _LOGGER.error(f"Unexpected error during API validation: {err}")
            raise CannotConnect from err

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        from .options_flow import MailcowOptionsFlowHandler
        return MailcowOptionsFlowHandler(config_entry)


