from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

class MailcowContainerBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, container_id: str, container_name: str) -> None:
        super().__init__(coordinator)
        self._container_id = container_id
        self._container_name = container_name
        self._attr_name = f"Mailcow Container {container_name}"
        self._attr_unique_id = f"mailcow_container_{container_id}_{coordinator.entry_id}"

    @property
    def is_on(self) -> bool:
        """Le conteneur est 'on' si état running."""
        containers = self.coordinator.data.get("containers_status", [])
        container = next(
            (c for c in containers if c.get("id") == self._container_id or c.get("name") == self._container_name),
            None
        )
        if container:
            return container.get("state") == "running"
        return False

    @property
    def icon(self):
        """Icone dynamique selon l'état (vert si running, rouge sinon)."""
        if self.is_on:
            return "mdi:checkbox-marked-circle-outline"  # vert par défaut dans HA
        else:
            return "mdi:alert-circle-outline"  # rouge par défaut dans HA
    @property
    def name(self) -> str:
        return f"Mailcow Container {self._container_name}"
    
    @property
    def unique_id(self) -> str:
        return f"mailcow_container_{self._container_id}_{self.coordinator.entry_id}"
