"""Platform for sensor integration."""
import logging

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


class MailcowMailboxCountSensor(MailcowSensor):
    """Representation of a Mailcow mailbox count sensor."""

    def __init__(self, api: MailcowAPI, base_url: str):
        super().__init__(api, base_url)
        self._attr_name = "Mailcow Mailbox Count"
        self._attr_unique_id = f"mailcow_mailbox_count_{''.join(filter(str.isalnum, self._base_url))}"
        self._attr_icon = "mdi:email-multiple"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            mailbox_count = await self.api.get_mailbox_count()
            if mailbox_count is not None:
                self._attr_native_value = int(mailbox_count)  # Ensure it's an integer
                _LOGGER.debug(f"Mailbox count updated to: {self._attr_native_value}")
            else:
                _LOGGER.warning("Mailbox count is None, not updating state")
        except Exception as e:
            _LOGGER.error(f"Error getting mailbox count: {e}")
            self._attr_native_value = None  # Set state to None on error


class MailcowDomainCountSensor(MailcowSensor):
    """Representation of a Mailcow domain count sensor."""

    def __init__(self, api: MailcowAPI, base_url: str):
        super().__init__(api, base_url)
        self._attr_name = "Mailcow Domain Count"
        self._attr_unique_id = f"mailcow_domain_count_{''.join(filter(str.isalnum, self._base_url))}"
        self._attr_icon = "mdi:domain"

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        try:
            domain_count = await self.api.get_domain_count()
            if domain_count is not None:
                self._attr_native_value = int(domain_count)  # Ensure it's an integer
                _LOGGER.debug(f"Domain count updated to: {self._attr_native_value}")
            else:
                _LOGGER.warning("Domain count is None, not updating state")
        except Exception as e:
            _LOGGER.error(f"Error getting domain count: {e}")
            self._attr_native_value = None  # Set state to None on error


class MailcowVersionSensor(MailcowSensor):
    """Representation of a Mailcow version sensor."""

    def __init__(self, api: MailcowAPI, base_url: str):
        super().__init__(api, base_url)
        self._attr_name = "Mailcow Version"
        self._attr_unique_id = f"mailcow_version_{''.join(filter(str.isalnum, self._base_url))}"
        self._attr_icon = "mdi:package-variant"
        self._attr_state_class = None

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        _LOGGER.debug("Starting update for MailcowVersionSensor")
        try:
            version = await self.api.get_status_version()
            _LOGGER.debug(f"Received version data: {version}")
            if version is not None:
                self._attr_native_value = str(version)  # Ensure it's a string
                self._attr_extra_state_attributes = {"version": version}
                self.device_info["sw_version"] = version  # Update device info
                _LOGGER.debug(f"Mailcow version updated to: {self._attr_native_value}")
            else:
                _LOGGER.warning("Version info is None, not updating state")
        except Exception as e:
            _LOGGER.exception(f"Error getting Mailcow version: {e}")
            self._attr_native_value = None  # Set state to None on error

class MailcowVmailStatusSensor(MailcowSensor):
    def __init__(self, api: MailcowAPI, base_url: str):
        super().__init__(api, base_url)
        self._attr_name = "Mailcow Vmail Disk Usage"
        self._attr_unique_id = f"mailcow_vmail_disk_usage_{''.join(filter(str.isalnum, self._base_url))}"
        self._attr_icon = "mdi:harddisk"
        self._attr_state_class = None
        self._attr_native_unit_of_measurement = "%"

    async def async_update(self) -> None:
        try:
            vmail_status = await self.api.get_status_vmail()
            if vmail_status:
                # Remove the '%' sign and convert to float
                used_percent = float(vmail_status.get("used_percent", "0").rstrip('%'))
                self._attr_native_value = used_percent
                self._attr_extra_state_attributes = {
                    "status": "OK" if vmail_status.get("type") == "info" else "Error",
                    "disk": vmail_status.get("disk"),
                    "used": vmail_status.get("used"),
                    "total": vmail_status.get("total"),
                    "type": vmail_status.get("type")
                }
            else:
                self._attr_native_value = None
                self._attr_extra_state_attributes = {}
        except Exception as e:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            _LOGGER.error(f"Error getting vmail status: {e}")

class MailcowContainersStatusSensor(MailcowSensor):
    def __init__(self, api: MailcowAPI, base_url: str):
        super().__init__(api, base_url)
        self._attr_name = "Mailcow Containers Status"
        self._attr_unique_id = f"mailcow_containers_status_{''.join(filter(str.isalnum, self._base_url))}"
        self._attr_icon = "mdi:docker"
        self._attr_state_class = None

    async def async_update(self) -> None:
        try:
            containers_status = await self.api.get_status_containers()
            if containers_status:
                all_running = all(container["state"] == "running" for container in containers_status.values())
                self._attr_native_value = "All Running" if all_running else "Issues Detected"
                self._attr_extra_state_attributes = {
                    container_name: {
                        "state": info["state"],
                        "started_at": info["started_at"],
                        "image": info["image"]
                    } for container_name, info in containers_status.items()
                }
            else:
                self._attr_native_value = "Unknown"
                self._attr_extra_state_attributes = {}
        except Exception as e:
            self._attr_native_value = "Error"
            self._attr_extra_state_attributes = {}
            _LOGGER.error(f"Error getting containers status: {e}")

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
