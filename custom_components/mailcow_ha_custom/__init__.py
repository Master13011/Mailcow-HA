import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS, CONF_SCAN_INTERVAL, CONF_DISABLE_CHECK_AT_NIGHT, CONF_BASE_URL, CONF_API_KEY
from .coordinator import MailcowCoordinator
from .api import MailcowAPI

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mailcow from a config entry."""
    _LOGGER.debug(f"Setting up Mailcow entry {entry.entry_id}")
    session = async_get_clientsession(hass)

    base_url = entry.data.get(CONF_BASE_URL)
    api_key = entry.options.get(CONF_API_KEY) or entry.data.get(CONF_API_KEY)

    if base_url is None or api_key is None:
        _LOGGER.error("Missing base_url or api_key in config entry")
        return False

    api = MailcowAPI({"base_url": base_url, "api_key": api_key}, session)

    coordinator = MailcowCoordinator(
        hass,
        api,
        entry.options.get(CONF_SCAN_INTERVAL, 10),
        entry.options.get(CONF_DISABLE_CHECK_AT_NIGHT, False),
        entry.entry_id,
        base_url,
        session
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info(f"Mailcow entry {entry.entry_id} set up successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug(f"Unloading Mailcow entry {entry.entry_id}")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info(f"Mailcow entry {entry.entry_id} unloaded successfully")
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    _LOGGER.debug(f"Reloading Mailcow entry {entry.entry_id}")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries to move API key to options."""
    data = dict(entry.data)
    options = dict(entry.options)
    updated = False

    if CONF_API_KEY in data:
        options.setdefault(CONF_API_KEY, data.pop(CONF_API_KEY))
        updated = True

    if updated:
        hass.config_entries.async_update_entry(entry, data=data, options=options)
        _LOGGER.info("Migrated Mailcow config entry to move api_key to options.")

    return True
