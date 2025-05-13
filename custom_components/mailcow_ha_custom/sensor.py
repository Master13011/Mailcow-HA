import logging
from datetime import datetime, timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def sanitize_url(url: str) -> str:
    return ''.join(filter(str.isalnum, url))

def is_night_time() -> bool:
    now = datetime.now().hour
    return now >= 23 or now < 5

class MailcowCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, scan_interval: int, disable_check_at_night: bool, entry_id: str, base_url: str):
        super().__init__(
            hass,
            _LOGGER,
            name="Mailcow Coordinator",
            update_interval=timedelta(minutes=scan_interval),
        )
        self.api = api
        self.disable_check_at_night = disable_check_at_night
        self.entry_id = entry_id
        self._base_url = base_url
        self._cached_latest_version = None

    async def fetch_latest_github_version(self):
        import aiohttp
        github_url = "https://api.github.com/repos/mailcow/mailcow-dockerized/tags"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(github_url) as response:
                    if response.status == 200:
                        tags = await response.json()
                        if tags:
                            sorted_tags = sorted(tags, key=lambda x: x["name"], reverse=True)
                            return sorted_tags[0]["name"]
        except Exception as e:
            _LOGGER.error(f"Error fetching GitHub version: {e}")
        return "unknown"

    async def _async_update_data(self):
        if self.disable_check_at_night and is_night_time():
            _LOGGER.debug("Night check disabled; skipping data update.")
            return self.data or {}
        try:
            version = await self.api.get_status_version()
            mailbox_count = await self.api.get_mailbox_count()
            domain_count = await self.api.get_domain_count()
            vmail_status = await self.api.get_status_vmail()
            containers_status = await self.api.get_status_containers()

            if not self._cached_latest_version:
                self._cached_latest_version = await self.fetch_latest_github_version()

            return {
                "version": version,
                "mailbox_count": mailbox_count,
                "domain_count": domain_count,
                "vmail_status": vmail_status,
                "containers_status": containers_status,
                "latest_version": self._cached_latest_version,
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

class MailcowSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, name: str, key: str, icon: str):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon
        self._key = key
        self._base_url = coordinator._base_url
        self._entry_id = coordinator.entry_id
        self._attr_unique_id = f"mailcow_{key}_{sanitize_url(self._base_url)}_{self._entry_id}"
        self._attr_state_class = None

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

class MailcowDomainCountSensor(MailcowSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Mailcow Domain Count", "domain_count", "mdi:domain")

class MailcowMailboxCountSensor(MailcowSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Mailcow Mailbox Count", "mailbox_count", "mdi:email-multiple")

class MailcowVersionSensor(MailcowSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Mailcow Version", "version", "mdi:package-variant")

class MailcowVmailStatusSensor(MailcowSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Mailcow Vmail Status", "vmail_status", "mdi:harddisk")
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        vmail_status = self.coordinator.data.get("vmail_status") or {}
        used_str = vmail_status.get("used_percent", "0")
        return float(used_str.rstrip('%')) if used_str.endswith('%') else float(used_str)

    @property
    def extra_state_attributes(self):
        status = self.coordinator.data.get("vmail_status") or {}
        return {
            "status": status.get("type"),
            "disk": status.get("disk"),
            "used": status.get("used"),
            "total": status.get("total")
        }
        
class MailcowContainersStatusSensor(MailcowSensor):
    def __init__(self, coordinator):
        super().__init__(coordinator, "Mailcow Containers Status", "containers_status", "mdi:docker")
        self._attr_device_class = None
    @property
    def native_value(self):
        containers = self.coordinator.data.get("containers_status") or {}
        return "All Running" if all(c.get("state") == "running" for c in containers.values()) else "Issues Detected"

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("containers_status", {})

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    sensors = [
        MailcowVersionSensor(coordinator),
        MailcowMailboxCountSensor(coordinator),
        MailcowDomainCountSensor(coordinator),
        MailcowVmailStatusSensor(coordinator),
        MailcowContainersStatusSensor(coordinator),
    ]
    async_add_entities(sensors, True)
