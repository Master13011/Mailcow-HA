"""Sensors for the Mailcow integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import MailcowConfigEntry, MailcowCoordinator
from .entity import MailcowEntity
from .util import containers_attributes, containers_state, vmail_percent

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MailcowSensorEntityDescription(SensorEntityDescription):
    """Describes a Mailcow sensor."""

    value_fn: Callable[[dict[str, Any]], StateType]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSOR_TYPES: tuple[MailcowSensorEntityDescription, ...] = (
    MailcowSensorEntityDescription(
        key="version",
        translation_key="version",
        icon="mdi:package-variant",
        value_fn=lambda data: data.get("version"),
    ),
    MailcowSensorEntityDescription(
        key="mailbox_count",
        translation_key="mailbox_count",
        icon="mdi:email-multiple",
        value_fn=lambda data: data.get("mailbox_count"),
    ),
    MailcowSensorEntityDescription(
        key="domain_count",
        translation_key="domain_count",
        icon="mdi:domain",
        value_fn=lambda data: data.get("domain_count"),
    ),
    MailcowSensorEntityDescription(
        key="vmail_status",
        translation_key="vmail_status",
        icon="mdi:harddisk",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: vmail_percent(data.get("vmail_status")),
        attrs_fn=lambda data: {
            "status": (data.get("vmail_status") or {}).get("type"),
            "disk": (data.get("vmail_status") or {}).get("disk"),
            "used": (data.get("vmail_status") or {}).get("used"),
            "total": (data.get("vmail_status") or {}).get("total"),
        },
    ),
    MailcowSensorEntityDescription(
        key="containers_status",
        translation_key="containers_status",
        icon="mdi:docker",
        value_fn=lambda data: containers_state(data.get("containers_status")),
        attrs_fn=lambda data: containers_attributes(data.get("containers_status")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MailcowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Mailcow sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        MailcowSensor(coordinator, description) for description in SENSOR_TYPES
    )


class MailcowSensor(MailcowEntity, SensorEntity):
    """A Mailcow sensor."""

    entity_description: MailcowSensorEntityDescription

    def __init__(
        self,
        coordinator: MailcowCoordinator,
        description: MailcowSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data or {})
