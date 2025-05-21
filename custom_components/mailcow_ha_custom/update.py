from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

def sanitize_url(url: str) -> str:
    return ''.join(filter(str.isalnum, url))

class MailcowUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Représente la mise à jour Mailcow."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Mailcow Update"
        self._attr_unique_id = f"mailcow_update_{sanitize_url(getattr(coordinator, '_base_url', ''))}_{getattr(coordinator, 'entry_id', '')}"
        self._attr_device_class = "update"
        self._entry_id = getattr(coordinator, "entry_id", None) 

    @property
    def installed_version(self):
        return self.coordinator.data.get("version")

    @property
    def latest_version(self):
        return self.coordinator.data.get("latest_version")

    @property
    def in_progress(self):
        return False

    @property
    def title(self):
        return "Mailcow"
        
    @property
    def extra_state_attributes(self):
        return {
            "installed_version": self.coordinator.data.get("version", "unknown"),
            "latest_version": self.coordinator.data.get("latest_version", "unknown"),
            "release_url": "https://github.com/mailcow/mailcow-dockerized/releases"
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Mailcow HA",
            "manufacturer": "Master13011",
            "model": "API",
            "sw_version": self.coordinator.data.get("version", "unknown"),
        }
        
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Mailcow HA",
            "manufacturer": "Master13011",
            "model": "API",
            "sw_version": self.coordinator.data.get("version", "unknown"),
        } 
    async def async_install(self, version, backup, **kwargs):
        # Implémente ici la logique d'installation de la mise à jour Mailcow si tu veux
        pass

    async def async_update(self):
        await self.coordinator.async_request_refresh()

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([MailcowUpdateEntity(coordinator)], True)
