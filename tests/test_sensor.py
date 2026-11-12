"""Tests of the Mailcow sensors."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.mailcow_ha_custom.const import DOMAIN
from custom_components.mailcow_ha_custom.sensor import SENSOR_TYPES, MailcowSensor

from .common import BASE_URL, CONTAINERS, VMAIL, make_entry, setup_entry, unique_id


def _description(key: str):
    return next(d for d in SENSOR_TYPES if d.key == key)


def _sensor(key: str, data) -> MailcowSensor:
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry_1"
    coordinator.base_url = BASE_URL
    coordinator.data = data
    return MailcowSensor(coordinator, _description(key))


def _state(hass: HomeAssistant, entry, key: str):
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id(entry, key))
    assert entity_id is not None, f"no sensor registered for {key}"
    state = hass.states.get(entity_id)
    assert state is not None
    return state


# --- descriptions ------------------------------------------------------------------


def test_sensor_keys() -> None:
    assert [d.key for d in SENSOR_TYPES] == [
        "version",
        "mailbox_count",
        "domain_count",
        "vmail_status",
        "containers_status",
    ]


def test_every_sensor_has_a_translation_key_and_an_icon() -> None:
    for description in SENSOR_TYPES:
        assert description.translation_key == description.key
        assert description.icon


def test_vmail_is_a_percentage_measurement() -> None:
    description = _description("vmail_status")
    assert description.native_unit_of_measurement == "%"
    assert description.state_class is SensorStateClass.MEASUREMENT


# --- values and attributes (without Home Assistant) --------------------------------------


def test_values_from_complete_data() -> None:
    data = {
        "version": "2025-03a",
        "mailbox_count": 3,
        "domain_count": 2,
        "vmail_status": VMAIL,
        "containers_status": CONTAINERS,
    }
    assert _sensor("version", data).native_value == "2025-03a"
    assert _sensor("mailbox_count", data).native_value == 3
    assert _sensor("domain_count", data).native_value == 2
    assert _sensor("vmail_status", data).native_value == 55.0
    assert _sensor("containers_status", data).native_value == "All Running"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("version", None),
        ("mailbox_count", None),
        ("domain_count", None),
        ("vmail_status", None),
        ("containers_status", "N/A"),
    ],
)
@pytest.mark.parametrize("data", [{}, None])
def test_values_without_data(key, expected, data) -> None:
    assert _sensor(key, data).native_value == expected


def test_simple_sensors_have_no_attributes() -> None:
    for key in ("version", "mailbox_count", "domain_count"):
        assert _sensor(key, {"version": "x"}).extra_state_attributes is None


def test_vmail_attributes() -> None:
    sensor = _sensor("vmail_status", {"vmail_status": VMAIL})
    assert sensor.extra_state_attributes == {
        "status": "info",
        "disk": "/dev/sda1",
        "used": "5G",
        "total": "10G",
    }


@pytest.mark.parametrize("data", [{}, None, {"vmail_status": None}])
def test_vmail_attributes_without_data(data) -> None:
    assert _sensor("vmail_status", data).extra_state_attributes == {
        "status": None,
        "disk": None,
        "used": None,
        "total": None,
    }


def test_containers_attributes_from_a_dict_and_a_list() -> None:
    assert _sensor("containers_status", {"containers_status": CONTAINERS}).extra_state_attributes == CONTAINERS

    as_list = [{"container": "nginx-mailcow", "state": "running"}]
    attributes = _sensor("containers_status", {"containers_status": as_list}).extra_state_attributes
    assert attributes == {"nginx-mailcow": as_list[0]}


def test_containers_attributes_without_data() -> None:
    assert _sensor("containers_status", None).extra_state_attributes == {}


def test_unavailable_vmail_value() -> None:
    sensor = _sensor("vmail_status", {"vmail_status": {"used_percent": "n/a"}})
    assert sensor.native_value is None


# --- with Home Assistant ------------------------------------------------------------------


async def test_sensor_states(hass: HomeAssistant, mailcow_api: MagicMock) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)

    assert _state(hass, entry, "version").state == "2025-03a"
    assert _state(hass, entry, "mailbox_count").state == "3"
    assert _state(hass, entry, "domain_count").state == "2"
    assert _state(hass, entry, "containers_status").state == "All Running"

    vmail = _state(hass, entry, "vmail_status")
    assert float(vmail.state) == 55.0
    assert vmail.attributes["unit_of_measurement"] == "%"
    assert vmail.attributes["disk"] == "/dev/sda1"
    assert vmail.attributes["used"] == "5G"
    assert vmail.attributes["total"] == "10G"


async def test_containers_sensor_lists_every_container(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)

    attributes = _state(hass, entry, "containers_status").attributes
    assert attributes["nginx-mailcow"]["state"] == "running"
    assert attributes["postfix-mailcow"]["state"] == "running"


async def test_containers_sensor_detects_a_stopped_container(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    mailcow_api.get_status_containers.return_value = {
        "nginx-mailcow": {"container": "nginx-mailcow", "state": "running"},
        "postfix-mailcow": {"container": "postfix-mailcow", "state": "exited"},
    }
    entry = make_entry()
    await setup_entry(hass, entry)

    assert _state(hass, entry, "containers_status").state == "Issues Detected"


async def test_sensors_with_missing_values_are_unknown(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    mailcow_api.get_mailbox_count.return_value = None
    mailcow_api.get_domain_count.return_value = None
    mailcow_api.get_status_vmail.return_value = {}
    entry = make_entry()
    await setup_entry(hass, entry)

    assert _state(hass, entry, "mailbox_count").state == "unknown"
    assert _state(hass, entry, "domain_count").state == "unknown"
    assert _state(hass, entry, "vmail_status").state == "unknown"


async def test_unique_ids_keep_the_historical_format(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)

    registry = er.async_get(hass)
    for key in ("version", "mailbox_count", "domain_count", "vmail_status", "containers_status"):
        expected = f"mailcow_{key}_httpsmailexamplecom_{entry.entry_id}"
        assert registry.async_get_entity_id("sensor", DOMAIN, expected) is not None
