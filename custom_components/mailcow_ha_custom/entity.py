"""Base entity for the Mailcow integration."""

from __future__ import annotations

from urllib.parse import urlsplit

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MailcowCoordinator
from .util import sanitize_url


class MailcowEntity(CoordinatorEntity[MailcowCoordinator]):
    """Base class for all Mailcow entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MailcowCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        # Format kept identical to previous versions so entities are not duplicated.
        self._attr_unique_id = (
            f"mailcow_{key}_{sanitize_url(coordinator.base_url)}_{entry_id}"
        )

    @property
    def device_info(self) -> DeviceInfo:
        coordinator = self.coordinator
        data = coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=f"Mailcow ({urlsplit(coordinator.base_url).netloc})",
            manufacturer="Mailcow",
            model="mailcow-dockerized",
            sw_version=data.get("version"),
            configuration_url=coordinator.base_url,
            entry_type=DeviceEntryType.SERVICE,
        )
