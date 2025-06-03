import logging
from urllib.parse import urlparse
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def sanitize_url(url: str) -> str:
    return ''.join(filter(str.isalnum, url))

class MailcowSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, name: str, key: str, icon: str):
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_icon = icon
        self._key = key
        self._base_url = coordinator._base_url
        self._entry_id = coordinator.entry_id
        self._attr_unique_id = (
            f"mailcow_{key}_{sanitize_url(coordinator._base_url)}_{coordinator.entry_id}"
        )
        self._attr_state_class = None

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "manufacturer": "Master13011",
            "model": "API",
            "name": urlparse(self._base_url).netloc,
            "sw_version": self.coordinator.data.get("version", "unknown"),
        }

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
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        vmail_status = self.coordinator.data.get("vmail_status") or {}
        used_str = vmail_status.get("used_percent", "0")
        try:
            return float(used_str.rstrip('%'))
        except (ValueError, AttributeError):
            _LOGGER.warning("Invalid vmail_status used_percent value: %s", used_str)
            return 0.0
        
    @property
    def native_unit_of_measurement(self):
        return "%"
    
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
        containers = self.coordinator.data.get("containers_status")
        # Si containers est une liste de dicts
        if isinstance(containers, list) and all(isinstance(c, dict) for c in containers):
            if not containers:
                return "No Data"
            return "All Running" if all(c.get("state") == "running" for c in containers) else "Issues Detected"
        # Si containers est un dict (pour compatibilité descendante)
        if isinstance(containers, dict):
            if not containers:
                return "No Data"
            return "All Running" if all(c.get("state") == "running" for c in containers.values()) else "Issues Detected"
        return "Unknown"

    @property
    def extra_state_attributes(self):
        containers = self.coordinator.data.get("containers_status")
        return containers if isinstance(containers, (list, dict)) else {}

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
