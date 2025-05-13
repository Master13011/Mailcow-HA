"""The Mailcow integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_API_KEY, CONF_BASE_URL, CONF_DISABLE_CHECK_AT_NIGHT, CONF_SCAN_INTERVAL
from .api import MailcowAPI
from .sensor import MailcowCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "update"]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Mailcow component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Mailcow from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    base_url = entry.data[CONF_BASE_URL]
    api_key = entry.data[CONF_API_KEY]
    disable_check_at_night = entry.options.get(CONF_DISABLE_CHECK_AT_NIGHT, False)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, 10)

    _LOGGER.debug(f"Setting up Mailcow integration with base URL: {base_url}")

    api = MailcowAPI(base_url, api_key, hass)  # Pass hass to the API
    coordinator = MailcowCoordinator(
        hass,
        api,
        scan_interval,
        disable_check_at_night,
        entry.entry_id,
        base_url,
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator
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
        coordinator = hass.data[DOMAIN][entry.entry_id]  # Correction ici
        await coordinator.api.close_session()  # Appel correct sur l'API
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.info("Mailcow integration unloaded successfully.")
    else:
        _LOGGER.warning("Mailcow integration failed to unload.")
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle reload of an entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
