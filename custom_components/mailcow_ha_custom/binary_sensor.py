from homeassistant.components.binary_sensor import BinarySensorEntity
from .const import DOMAIN

class MailcowContainersHealthyBinarySensor(BinarySensorEntity):
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_name = "Mailcow Containers Healthy"
        self._attr_unique_id = f"{DOMAIN}_containers_healthy_{coordinator.entry_id}"
        self._attr_icon = "mdi:check-circle"

    @property
    def is_on(self):
        containers = self.coordinator.data.get("containers_status", {})
        return all(c.get("state") == "running" for c in containers.values())

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("containers_status", {})
