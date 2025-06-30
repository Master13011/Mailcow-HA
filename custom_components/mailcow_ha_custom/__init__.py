import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.config import ConfigType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
import aiohttp

from .const import DOMAIN, PLATFORMS, CONF_SCAN_INTERVAL, CONF_DISABLE_CHECK_AT_NIGHT, CONF_BASE_URL
from .coordinator import MailcowCoordinator
from .api import MailcowAPI

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Mailcow component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("Mailcow component set up")
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mailcow from a config entry."""
    _LOGGER.debug(f"Setting up Mailcow entry {entry.entry_id}")
    session: aiohttp.ClientSession = async_get_clientsession(hass)
    api = MailcowAPI(entry.data, session)

    coordinator = MailcowCoordinator(
        hass,
        api,
        entry.options.get(CONF_SCAN_INTERVAL, 10),
        entry.options.get(CONF_DISABLE_CHECK_AT_NIGHT, False),
        entry.entry_id,
        entry.data.get(CONF_BASE_URL),
        session
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info(f"Mailcow entry {entry.entry_id} set up successfully")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug(f"Unloading Mailcow entry {entry.entry_id}")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info(f"Mailcow entry {entry.entry_id} unloaded successfully")
    else:
        _LOGGER.warning(f"Failed to unload Mailcow entry {entry.entry_id}")
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle reload of an entry."""
    _LOGGER.debug(f"Reloading Mailcow entry {entry.entry_id}")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
