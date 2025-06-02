import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.config import ConfigType
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS, CONF_SCAN_INTERVAL, CONF_DISABLE_CHECK_AT_NIGHT, CONF_BASE_URL
from .coordinator import MailcowCoordinator
from .api import MailcowAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Mailcow component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mailcow from a config entry."""
    session = async_get_clientsession(hass)
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
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle reload of an entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
