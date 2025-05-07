"""The Mailcow integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_API_KEY, CONF_BASE_URL
from .config_flow import MailcowOptionsFlowHandler
from .api import MailcowAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Mailcow component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mailcow from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    base_url = entry.data[CONF_BASE_URL]
    api_key = entry.data[CONF_API_KEY]

    _LOGGER.debug(f"Setting up Mailcow integration with base URL: {base_url}")

    api = MailcowAPI(base_url, api_key, hass)  # Pass hass to the API
    hass.data[DOMAIN][entry.entry_id] = api

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _LOGGER.info("Mailcow integration setup completed successfully.")
        return True
    except Exception as e:
        _LOGGER.error(f"Error during setup: {e}")
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Mailcow integration.")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        api = hass.data[DOMAIN][entry.entry_id]  # Get the API instance
        await api.close_session()  # Close the session
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Mailcow integration unloaded successfully.")
    else:
        _LOGGER.warning("Mailcow integration failed to unload.")
    return unload_ok

async def async_get_options_flow(config_entry: ConfigEntry):
    return MailcowOptionsFlowHandler(config_entry)
