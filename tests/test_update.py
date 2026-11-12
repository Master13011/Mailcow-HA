"""Tests of the Mailcow update entity (informational)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.mailcow_ha_custom.const import DOMAIN, GITHUB_RELEASES_PAGE
from custom_components.mailcow_ha_custom.update import MailcowUpdateEntity

from .common import BASE_URL, make_entry, setup_entry, unique_id


def _entity(data) -> MailcowUpdateEntity:
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry_1"
    coordinator.base_url = BASE_URL
    coordinator.data = data
    return MailcowUpdateEntity(coordinator)


def _state(hass: HomeAssistant, entry):
    entity_id = er.async_get(hass).async_get_entity_id("update", DOMAIN, unique_id(entry, "update"))
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    return state


# --- without Home Assistant ----------------------------------------------------------------


def test_versions_come_from_the_coordinator() -> None:
    entity = _entity({"version": "2025-03a", "latest_version": "2025-04"})
    assert entity.installed_version == "2025-03a"
    assert entity.latest_version == "2025-04"


@pytest.mark.parametrize("data", [{}, None])
def test_versions_without_data(data) -> None:
    entity = _entity(data)
    assert entity.installed_version is None
    assert entity.latest_version is None


def test_release_url_points_to_the_latest_tag() -> None:
    entity = _entity({"latest_version": "2025-04"})
    assert entity.release_url == f"{GITHUB_RELEASES_PAGE}/tag/2025-04"


def test_release_url_falls_back_to_the_releases_page() -> None:
    assert _entity({"latest_version": None}).release_url == GITHUB_RELEASES_PAGE
    assert _entity(None).release_url == GITHUB_RELEASES_PAGE


@pytest.mark.parametrize(
    ("latest", "installed", "expected"),
    [
        ("2025-04", "2025-03a", True),
        ("2025-03b", "2025-03a", True),
        ("2025-03a", "2025-03a", False),
        ("2025-03", "2025-03a", False),  # never suggest a downgrade
    ],
)
def test_version_comparison(latest, installed, expected) -> None:
    assert _entity({}).version_is_newer(latest, installed) is expected


def test_unique_id_and_title() -> None:
    entity = _entity({})
    assert entity.unique_id == "mailcow_update_httpsmailexamplecom_entry_1"
    assert entity.title == "Mailcow"


# --- with Home Assistant ------------------------------------------------------------------------


async def test_update_available(hass: HomeAssistant, mailcow_api: MagicMock) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)  # installed 2025-03a, latest 2025-04

    state = _state(hass, entry)
    assert state.state == "on"
    assert state.attributes["installed_version"] == "2025-03a"
    assert state.attributes["latest_version"] == "2025-04"
    assert state.attributes["release_url"] == f"{GITHUB_RELEASES_PAGE}/tag/2025-04"


async def test_up_to_date(hass: HomeAssistant, mailcow_api: MagicMock) -> None:
    mailcow_api.latest_mock.return_value = "2025-03a"
    entry = make_entry()
    await setup_entry(hass, entry)

    assert _state(hass, entry).state == "off"


async def test_installed_version_newer_than_the_published_one(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    mailcow_api.latest_mock.return_value = "2025-02"
    entry = make_entry()
    await setup_entry(hass, entry)

    assert _state(hass, entry).state == "off"


async def test_unknown_when_github_cannot_be_reached(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    mailcow_api.latest_mock.return_value = None
    entry = make_entry()
    await setup_entry(hass, entry)

    assert _state(hass, entry).state == "unknown"
