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
    CONF_DISABLE_CHECK_AT_NIGHT,
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
            vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=False): bool,
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
        return MailcowOptionsFlowHandler()  


class MailcowOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Mailcow."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            # Si l'utilisateur a soumis des options, on recharge l'entrée de configuration
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=user_input)

        # Accédez à self.config_entry directement
        disable_check_at_night = self.config_entry.options.get("disable_check_at_night", False)

        data_schema = vol.Schema({
            vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=disable_check_at_night): bool
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )


async def async_get_options_flow(config_entry):
    return MailcowOptionsFlowHandler(config_entry)
