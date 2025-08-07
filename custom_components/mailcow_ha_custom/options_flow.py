import voluptuous as vol
from homeassistant.config_entries import OptionsFlow, ConfigEntry
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_KEY,
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
)


class MailcowOptionsFlowHandler(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            options = {
                CONF_API_KEY: user_input.get(CONF_API_KEY, self.config_entry.options.get(CONF_API_KEY)),
                CONF_DISABLE_CHECK_AT_NIGHT: user_input.get(CONF_DISABLE_CHECK_AT_NIGHT, False),
                CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, 10),
            }
            self.hass.config_entries.async_update_entry(self.config_entry, options=options)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=options)

        disable_check_at_night = self.config_entry.options.get(CONF_DISABLE_CHECK_AT_NIGHT, False)
        scan_interval = self.config_entry.options.get(CONF_SCAN_INTERVAL, 10)
        api_key = self.config_entry.options.get(CONF_API_KEY, "")

        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY, default=api_key): str,
            vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=disable_check_at_night): bool,
            vol.Optional(CONF_SCAN_INTERVAL, default=scan_interval): vol.All(int, vol.Range(min=1)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,

        )



