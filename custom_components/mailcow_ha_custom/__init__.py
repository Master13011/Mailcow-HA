"""The Mailcow integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MailcowAPI, normalize_base_url
from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MailcowConfigEntry, MailcowCoordinator
from .exceptions import MailcowInvalidURLError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: MailcowConfigEntry) -> bool:
    """Set up Mailcow from a config entry."""
    api_key = entry.data.get(CONF_API_KEY)
    if not api_key:
        raise ConfigEntryAuthFailed("Missing API key")

    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    try:
        api = MailcowAPI(
            {CONF_BASE_URL: entry.data[CONF_BASE_URL], CONF_API_KEY: api_key},
            async_get_clientsession(hass, verify_ssl=verify_ssl),
        )
    except MailcowInvalidURLError as err:
        raise ConfigEntryError("Invalid Mailcow URL") from err

    # GitHub is always queried with a verified TLS session.
    coordinator = MailcowCoordinator(hass, entry, api, async_get_clientsession(hass))
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MailcowConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: MailcowConfigEntry) -> bool:
    """Migrate old config entries.

    Version 1 -> 2:
    - the API key moves back to `data` (needed for reauthentication);
    - `verify_ssl` is added (defaults to True, as before);
    - the base URL is normalized and used as the entry unique ID.
    """
    if entry.version > 2:
        return False

    if entry.version == 1:
        data = dict(entry.data)
        options = dict(entry.options)

        api_key = options.pop(CONF_API_KEY, None) or data.get(CONF_API_KEY)
        if api_key:
            data[CONF_API_KEY] = api_key
        data.setdefault(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

        unique_id = entry.unique_id
        base_url = data.get(CONF_BASE_URL)
        if base_url:
            try:
                data[CONF_BASE_URL] = normalize_base_url(base_url)
            except MailcowInvalidURLError:
                _LOGGER.warning("Stored Mailcow URL is invalid: %s", base_url)
            else:
                candidate = data[CONF_BASE_URL].lower()
                taken = any(
                    other.unique_id == candidate
                    for other in hass.config_entries.async_entries(DOMAIN)
                    if other.entry_id != entry.entry_id
                )
                if unique_id is None and not taken:
                    unique_id = candidate

        hass.config_entries.async_update_entry(
            entry, data=data, options=options, unique_id=unique_id, version=2
        )
        _LOGGER.info("Migrated Mailcow config entry to version 2")

    return True
