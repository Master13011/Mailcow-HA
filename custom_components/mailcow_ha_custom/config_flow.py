import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
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
                return self.async_create_entry(
                    title="Mailcow",
                    data={
                        CONF_BASE_URL: user_input[CONF_BASE_URL],
                        CONF_API_KEY: user_input[CONF_API_KEY],
                    },
                    options={
                        CONF_DISABLE_CHECK_AT_NIGHT: user_input.get(CONF_DISABLE_CHECK_AT_NIGHT, False),
                        CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 10),
                    },
                )
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
            vol.Optional(CONF_SCAN_INTERVAL, default=10): int,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _validate_input(self, user_input):
        """Validate the user input."""
        session = async_get_clientsession(self.hass)
        api = MailcowAPI(user_input, session)
        version = await api.get_status_version()
        if not version:
            raise CannotConnect

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return MailcowOptionsFlowHandler(config_entry)

class MailcowOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Mailcow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        disable_check_at_night = self.config_entry.options.get(CONF_DISABLE_CHECK_AT_NIGHT, False)
        scan_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, 10)

        data_schema = vol.Schema({
            vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=disable_check_at_night): bool,
            vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): int,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
