import logging
from urllib.parse import urlparse
from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

def sanitize_url(url: str) -> str:
    return ''.join(filter(str.isalnum, url))

class MailcowUpdateEntity(CoordinatorEntity, UpdateEntity):
    """Representation of a Mailcow update entity."""

    _attr_has_entity_name = True
    _attr_supported_features = UpdateEntityFeature.INSTALL
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Mailcow Update"
        self._attr_unique_id = (
            f"mailcow_update_{sanitize_url(coordinator._base_url)}_{coordinator.entry_id}"
        )
        self._base_url = coordinator._base_url
        self._entry_id = coordinator.entry_id

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "manufacturer": "Master13011",
            "model": "API",
            "name": urlparse(self._base_url).netloc,
            "sw_version": self.installed_version or "unknown",
        }

    @property
    def installed_version(self):
        return self.coordinator.data.get("version")

    @property
    def latest_version(self):
        return self.coordinator.data.get("latest_version")

    @property
    def release_url(self):
        latest = self.latest_version
        if latest and latest != "unknown":
            return f"https://github.com/mailcow/mailcow-dockerized/releases/tag/{latest}"
        return "https://github.com/mailcow/mailcow-dockerized/releases"

    @property
    def title(self):
        return "Mailcow"

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([MailcowUpdateEntity(coordinator)], True)
