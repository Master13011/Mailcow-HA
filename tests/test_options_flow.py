"""Tests of the options flow (night pause and scan interval)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.mailcow_ha_custom.const import (
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
)

from .common import make_entry, setup_entry


def _suggested(result, name):
    for key in result["data_schema"].schema:
        if key == name:
            return (key.description or {}).get("suggested_value")
    raise AssertionError(f"{name} not in the form")


async def test_form_shows_the_current_options(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = make_entry(options={CONF_DISABLE_CHECK_AT_NIGHT: True, CONF_SCAN_INTERVAL: 30})
    await setup_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert _suggested(result, CONF_DISABLE_CHECK_AT_NIGHT) is True
    assert _suggested(result, CONF_SCAN_INTERVAL) == 30


async def test_options_are_saved_and_reloaded(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)
    assert entry.runtime_data.update_interval == timedelta(minutes=10)
    assert entry.runtime_data.disable_check_at_night is False

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_DISABLE_CHECK_AT_NIGHT: True, CONF_SCAN_INTERVAL: 15},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_DISABLE_CHECK_AT_NIGHT: True, CONF_SCAN_INTERVAL: 15}
    assert type(entry.options[CONF_SCAN_INTERVAL]) is int
    # The integration reloaded itself with the new settings
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.update_interval == timedelta(minutes=15)
    assert entry.runtime_data.disable_check_at_night is True


async def test_default_values_when_nothing_is_entered(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = make_entry(options={CONF_DISABLE_CHECK_AT_NIGHT: True, CONF_SCAN_INTERVAL: 30})
    await setup_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_DISABLE_CHECK_AT_NIGHT: False, CONF_SCAN_INTERVAL: 10}


@pytest.mark.parametrize("value", [0, -1, 1441])
async def test_out_of_range_interval_is_refused(
    hass: HomeAssistant, mailcow_api: MagicMock, value
) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: value}
        )


@pytest.mark.parametrize("value", [1, 1440])
async def test_interval_limits_are_accepted(
    hass: HomeAssistant, mailcow_api: MagicMock, value
) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: value}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == value
