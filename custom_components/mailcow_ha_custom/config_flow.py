import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
    CONF_NIGHT_START_HOUR,
    CONF_NIGHT_END_HOUR,
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
        default_start = 23
        default_end = 5
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
                        CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 10),
                        CONF_DISABLE_CHECK_AT_NIGHT: user_input.get(CONF_DISABLE_CHECK_AT_NIGHT, False),
                        CONF_NIGHT_START_HOUR: user_input.get(CONF_NIGHT_START_HOUR, default_start),
                        CONF_NIGHT_END_HOUR: user_input.get(CONF_NIGHT_END_HOUR, default_end),
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
            vol.Optional(CONF_NIGHT_START_HOUR, default=default_start): cv.positive_int,
            vol.Optional(CONF_NIGHT_END_HOUR, default=default_end): cv.positive_int,
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
        super().__init__()
        self._entry_id = config_entry.entry_id

    async def async_step_init(self, user_input=None):
        errors = {}
        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        initial_disable_check_at_night = entry.options.get(CONF_DISABLE_CHECK_AT_NIGHT, False)
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, 10)
        night_start_hour = entry.options.get(CONF_NIGHT_START_HOUR, 23)
        night_end_hour = entry.options.get(CONF_NIGHT_END_HOUR, 5)
    
        if user_input is not None:
            disable_check_at_night = user_input.get(CONF_DISABLE_CHECK_AT_NIGHT, False)
    
            # Si option désactivée, on supprime les champs heures pour éviter validation foireuse
            if not disable_check_at_night:
                user_input.pop(CONF_NIGHT_START_HOUR, None)
                user_input.pop(CONF_NIGHT_END_HOUR, None)
    
            # Sinon on valide la présence et la valeur des heures
            else:
                start = user_input.get(CONF_NIGHT_START_HOUR)
                end = user_input.get(CONF_NIGHT_END_HOUR)
    
                # Si vide ou None, erreur
                if start is None or end is None:
                    errors["base"] = "night_hours_required"
                else:
                    try:
                        start_int = int(start)
                        end_int = int(end)
                        if not (0 <= start_int <= 23) or not (0 <= end_int <= 23):
                            errors["base"] = "invalid_night_hours"
                    except Exception:
                        errors["base"] = "invalid_night_hours"
    
            # Si l'utilisateur vient de changer la valeur du switch, on recharge sans valider
            if disable_check_at_night != initial_disable_check_at_night:
                data_schema = self._get_data_schema(
                    disable_check_at_night,
                    user_input.get(CONF_SCAN_INTERVAL, scan_interval),
                    user_input.get(CONF_NIGHT_START_HOUR, night_start_hour),
                    user_input.get(CONF_NIGHT_END_HOUR, night_end_hour),
                )
                return self.async_show_form(step_id="init", data_schema=data_schema, errors={})
    
            if not errors:
                return self.async_create_entry(title="", data=user_input)
    
        data_schema = self._get_data_schema(
            initial_disable_check_at_night,
            scan_interval,
            night_start_hour,
            night_end_hour,
        )
        return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)

    def _get_data_schema(self, disable_check_at_night, scan_interval, night_start_hour, night_end_hour):
        # Utilise juste vol.Coerce(int) pour un champ numérique simple (pas de slider)
        hour_validator = vol.Coerce(int)
        schema_dict = {
            vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=disable_check_at_night): bool,
            vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): int,
        }
        if disable_check_at_night:
            schema_dict.update({
                vol.Optional(CONF_NIGHT_START_HOUR, default=night_start_hour): hour_validator,
                vol.Optional(CONF_NIGHT_END_HOUR, default=night_end_hour): hour_validator,
            })
        return vol.Schema(schema_dict)
