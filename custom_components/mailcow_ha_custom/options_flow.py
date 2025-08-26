import voluptuous as vol
from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.data_entry_flow import FlowResult
from typing import Any
from .const import (
    CONF_API_KEY,
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
)

OPTIONS_SCHEMA = vol.Schema({
    vol.Required(CONF_API_KEY): str,
    vol.Optional(CONF_DISABLE_CHECK_AT_NIGHT, default=False): bool,
    vol.Optional(CONF_SCAN_INTERVAL, default=10): vol.All(int, vol.Range(min=1)),
})

class MailcowOptionsFlowHandler(OptionsFlowWithReload):
    def __init__(self) -> None:
        super().__init__()

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data_schema = self.add_suggested_values_to_schema(
            OPTIONS_SCHEMA,
            self.config_entry.options
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
        )
