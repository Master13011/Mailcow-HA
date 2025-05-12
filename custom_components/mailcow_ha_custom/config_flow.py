import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback

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
                # Sépare les données de base et les options
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
        try:
            api = MailcowAPI(user_input[CONF_BASE_URL], user_input[CONF_API_KEY], self.hass)
            await self.hass.async_add_executor_job(api.get_status_version)
        except Exception as err:
            _LOGGER.error(f"Error during validation: {err}")
            # Si c'est une erreur d'authentification (exemple 403)
            if hasattr(err, "response") and err.response is not None and getattr(err.response, "status_code", None) == 403:
                raise AuthenticationError from err
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
            await self._apply_options(user_input)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=user_input)

        # Utilisation de self.config_entry pour obtenir les options existantes
        disable_check_at_night = self.config_entry.options.get("disable_check_at_night", False)
        scan_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, 10)
        
        data_schema = vol.Schema({
            vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=disable_check_at_night): bool,
            vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): int,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )

    async def _apply_options(self, user_input):
        """Apply options after modification."""
        # Les options à appliquer
        options = {
            CONF_DISABLE_CHECK_AT_NIGHT: user_input.get(CONF_DISABLE_CHECK_AT_NIGHT, False),
            CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 10),
        }

        # Mise à jour des options via self.config_entry
        if self.config_entry:
            self.hass.config_entries.async_update_entry(self.config_entry, options=options)
