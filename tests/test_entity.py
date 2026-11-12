"""Tests of the base entity (unique ids and device)."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntryType

from custom_components.mailcow_ha_custom.const import DOMAIN
from custom_components.mailcow_ha_custom.entity import MailcowEntity

from .common import BASE_URL, make_api, make_entry, setup_entry


def _coordinator(data, entry_id="entry_1", base_url=BASE_URL) -> MagicMock:
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = entry_id
    coordinator.base_url = base_url
    coordinator.data = data
    return coordinator


def test_unique_id_format_is_unchanged() -> None:
    """The format comes from previous versions: changing it would duplicate entities."""
    entity = MailcowEntity(_coordinator({}), "version")
    assert entity.unique_id == "mailcow_version_httpsmailexamplecom_entry_1"


def test_unique_id_depends_on_key_url_and_entry() -> None:
    first = MailcowEntity(_coordinator({}), "version").unique_id
    other_key = MailcowEntity(_coordinator({}), "domain_count").unique_id
    other_url = MailcowEntity(_coordinator({}, base_url="https://mx.example.org"), "version").unique_id
    other_entry = MailcowEntity(_coordinator({}, entry_id="entry_2"), "version").unique_id
    assert len({first, other_key, other_url, other_entry}) == 4


def test_entity_name_is_relative_to_the_device() -> None:
    assert MailcowEntity(_coordinator({}), "version").has_entity_name is True


def test_device_info() -> None:
    entity = MailcowEntity(_coordinator({"version": "2025-03a"}), "version")
    info = entity.device_info

    assert info["identifiers"] == {(DOMAIN, "entry_1")}
    assert info["name"] == "Mailcow (mail.example.com)"
    assert info["manufacturer"] == "Mailcow"
    assert info["model"] == "mailcow-dockerized"
    assert info["sw_version"] == "2025-03a"
    assert info["configuration_url"] == BASE_URL
    assert info["entry_type"] is DeviceEntryType.SERVICE


def test_device_name_keeps_the_port() -> None:
    entity = MailcowEntity(_coordinator({}, base_url="https://mail.example.com:8443"), "version")
    assert entity.device_info["name"] == "Mailcow (mail.example.com:8443)"


def test_device_info_without_data() -> None:
    entity = MailcowEntity(_coordinator(None), "version")
    assert entity.device_info["sw_version"] is None


async def test_one_device_for_all_entities(hass: HomeAssistant, mailcow_api: MagicMock) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)

    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)

    assert len(devices) == 1
    assert devices[0].name == "Mailcow (mail.example.com)"
    assert devices[0].manufacturer == "Mailcow"
    assert devices[0].sw_version == "2025-03a"
    assert devices[0].entry_type is DeviceEntryType.SERVICE
