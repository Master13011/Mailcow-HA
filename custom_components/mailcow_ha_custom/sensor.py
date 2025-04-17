import logging
import aiohttp
from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .api import MailcowAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Mailcow sensors."""
    base_url = config_entry.data["base_url"]
    api = hass.data[DOMAIN][config_entry.entry_id]  # Get the API instance

    _LOGGER.debug("Setting up Mailcow sensors.")

    sensors = [
        MailcowMailboxCountSensor(api, base_url),
        MailcowDomainCountSensor(api, base_url),
        MailcowVersionSensor(api, base_url),
        MailcowVmailStatusSensor(api, base_url),
        MailcowContainersStatusSensor(api, base_url),
        MailcowUpdateAvailableSensor(api, base_url),  # New sensor
    ]

    async_add_entities(sensors, True)
    _LOGGER.info(f"Added {len(sensors)} Mailcow sensors.")


class MailcowSensor(SensorEntity):
    """Representation of a Mailcow sensor."""

    def __init__(self, api: MailcowAPI, base_url: str):
        """Initialize the sensor."""
        self.api = api
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._base_url = base_url
        self._attr_unique_id = None  # Will be set by child classes

    @property
    def device_info(self):
        """Return device information about this Mailcow instance."""
        return {
            "identifiers": {("mailcow", self._base_url)},
            "name": "Mailcow",
            "manufacturer": "Mailcow",
            "model": "API",
            "sw_version": "Unknown",  # This will be updated in the MailcowVersionSensor
        }


class MailcowUpdateAvailableSensor(MailcowSensor):
    """Representation of a Mailcow update available sensor."""

    def __init__(self, api: MailcowAPI, base_url: str):
        super().__init__(api, base_url)
        self._attr_name = "Mailcow Update Available"
        self._attr_unique_id = f"mailcow_update_available_{''.join(filter(str.isalnum, self._base_url))}"
        self._attr_icon = "mdi:package-up"  # Default icon
        self._attr_state_class = None

    async def fetch_latest_github_version(self):
        """Fetch the latest Mailcow version tag from GitHub."""
        github_url = "https://api.github.com/repos/mailcow/mailcow-dockerized/tags"
        async with aiohttp.ClientSession() as session:
            async with session.get(github_url) as response:
                if response.status == 200:
                    tags = await response.json()
                    if tags:
                        sorted_tags = sorted(tags, key=lambda x: x["name"], reverse=True)
                        return sorted_tags[0]["name"]
                return None

    async def async_update(self) -> None:
        _LOGGER.debug("Starting update for MailcowUpdateAvailableSensor")
        try:
            current_version = await self.api.get_status_version()
            latest_version = await self.fetch_latest_github_version()

            update_available = (
                latest_version != current_version
                if current_version and latest_version else None
            )

            self._attr_native_value = "Update available" if update_available else "Up to date"

            # Change icon to 'mdi:package-up' when update is available
            self._attr_icon = "mdi:package-up" if update_available else "mdi:package-check"

            self._attr_extra_state_attributes = {
                "installed_version": current_version,
                "latest_version": latest_version,
                "release_url": "https://github.com/mailcow/mailcow-dockerized/releases"
            }

        except Exception as e:
            _LOGGER.exception(f"Error checking update availability: {e}")
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}

