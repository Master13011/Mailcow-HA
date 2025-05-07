"""Config flow for Mailcow integration."""
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
import requests

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_BASE_URL,
    IS_NOT_CHECK_START_HOUR,
    IS_NOT_CHECK_END_HOUR,
)
from .api import MailcowAPI

_LOGGER = logging.getLogger(__name__)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class AuthenticationError(HomeAssistantError):
    """Error to indicate authentication failure."""


class MailcowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mailcow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                await self._validate_input(user_input)
                return self.async_create_entry(title="Mailcow", data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except Exception as e:
                _LOGGER.exception(f"Unexpected exception: {e}")
                errors["base"] = "unknown"

        data_schema = vol.Schema({
            vol.Required(CONF_BASE_URL): str,
            vol.Required(CONF_API_KEY): str,
            vol.Optional(IS_NOT_CHECK_START_HOUR, default=23): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
            vol.Optional(IS_NOT_CHECK_END_HOUR, default=5): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _validate_input(self, user_input):
        """Validate the user input."""
        try:
            api = MailcowAPI(user_input[CONF_BASE_URL], user_input[CONF_API_KEY], self.hass)
            await self.hass.async_add_executor_job(api.get_status_version)
        except requests.exceptions.RequestException as err:
            _LOGGER.error(f"Error during validation: {err}")
            if err.response is not None and err.response.status_code == 403:
                raise AuthenticationError from err
            else:
                raise CannotConnect from err
        except Exception as err:
            _LOGGER.error(f"Error during validation: {err}")
            raise CannotConnect from err
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MailcowOptionsFlowHandler(config_entry)

class MailcowOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Mailcow."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        default_start_hour = self.config_entry.options.get(
            IS_NOT_CHECK_START_HOUR,
            self.config_entry.data.get(IS_NOT_CHECK_START_HOUR, 23)
        )

        default_end_hour = self.config_entry.options.get(
            IS_NOT_CHECK_END_HOUR,
            self.config_entry.data.get(IS_NOT_CHECK_END_HOUR, 5)
        )

        data_schema = vol.Schema({
            vol.Optional(IS_NOT_CHECK_START_HOUR, default=default_start_hour): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
            vol.Optional(IS_NOT_CHECK_END_HOUR, default=default_end_hour): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )


async def async_get_options_flow(config_entry):
    return MailcowOptionsFlowHandler(config_entry)
