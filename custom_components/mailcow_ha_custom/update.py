"""Update entity for the Mailcow integration."""

from __future__ import annotations

from homeassistant.components.update import UpdateEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import GITHUB_RELEASES_PAGE
from .coordinator import MailcowConfigEntry, MailcowCoordinator
from .entity import MailcowEntity
from .util import is_newer

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MailcowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Mailcow update entity."""
    async_add_entities([MailcowUpdateEntity(entry.runtime_data)])


class MailcowUpdateEntity(MailcowEntity, UpdateEntity):
    """Tells whether a newer Mailcow version is available (informational)."""

    _attr_translation_key = "update"
    _attr_title = "Mailcow"

    def __init__(self, coordinator: MailcowCoordinator) -> None:
        super().__init__(coordinator, "update")

    @property
    def installed_version(self) -> str | None:
        return (self.coordinator.data or {}).get("version")

    @property
    def latest_version(self) -> str | None:
        return (self.coordinator.data or {}).get("latest_version")

    @property
    def release_url(self) -> str:
        latest = self.latest_version
        if latest:
            return f"{GITHUB_RELEASES_PAGE}/tag/{latest}"
        return GITHUB_RELEASES_PAGE

    def version_is_newer(self, latest_version: str, installed_version: str) -> bool:
        """Compare Mailcow date-based versions (e.g. 2025-03a)."""
        return is_newer(latest_version, installed_version)
