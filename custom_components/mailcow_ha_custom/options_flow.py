"""Options flow for the Mailcow integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import CONF_DISABLE_CHECK_AT_NIGHT, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL

OPTIONS_SCHEMA = vol.Schema(
    {
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


class MailcowOptionsFlowHandler(OptionsFlowWithReload):
    """Handle Mailcow options (the integration reloads automatically)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_DISABLE_CHECK_AT_NIGHT: bool(
                        user_input.get(CONF_DISABLE_CHECK_AT_NIGHT, False)
                    ),
                    CONF_SCAN_INTERVAL: int(
                        user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ),
                }
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
