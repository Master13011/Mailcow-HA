"""Tests of the setup, unload and migration of the integration."""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mailcow_ha_custom import async_migrate_entry
from custom_components.mailcow_ha_custom.const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.mailcow_ha_custom.coordinator import MailcowCoordinator
from custom_components.mailcow_ha_custom.exceptions import (
    MailcowAPIError,
    MailcowAuthenticationError,
    MailcowConnectionError,
)

from .common import BASE_URL, make_entry, setup_entry

# --- setup and unload --------------------------------------------------------------


async def test_setup_and_unload(hass: HomeAssistant, mailcow_api: MagicMock) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, MailcowCoordinator)
    assert entry.runtime_data.data["version"] == "2025-03a"
    assert entry.runtime_data.data["latest_version"] == "2025-04"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_platforms_create_five_sensors_and_one_update(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = make_entry()
    await setup_entry(hass, entry)

    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert sorted(e.domain for e in entities) == ["sensor"] * 5 + ["update"]


async def test_tls_verification_follows_the_entry(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = make_entry(**{CONF_VERIFY_SSL: False})
    with patch(
        "custom_components.mailcow_ha_custom.async_get_clientsession"
    ) as get_session:
        await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    # Mailcow session: verification disabled as configured
    assert get_session.call_args_list[0] == call(hass, verify_ssl=False)
    # GitHub session: always verified
    assert get_session.call_args_list[1] == call(hass)


async def test_tls_verification_defaults_to_enabled(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_BASE_URL: BASE_URL, CONF_API_KEY: "k"},
        unique_id=BASE_URL,
        version=2,
    )
    with patch(
        "custom_components.mailcow_ha_custom.async_get_clientsession"
    ) as get_session:
        await setup_entry(hass, entry)

    assert get_session.call_args_list[0] == call(hass, verify_ssl=True)


# --- setup failures -------------------------------------------------------------------


async def test_missing_api_key_asks_for_reauthentication(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    entry = make_entry(**{CONF_API_KEY: ""})
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


async def test_invalid_url_is_a_setup_error(hass: HomeAssistant) -> None:
    entry = make_entry(**{CONF_BASE_URL: "ftp://mail.example.com"})
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_rejected_api_key_asks_for_reauthentication(
    hass: HomeAssistant, mailcow_api: MagicMock
) -> None:
    mailcow_api.get_status_version.side_effect = MailcowAuthenticationError("bad key")
    entry = make_entry()
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)


@pytest.mark.parametrize(
    "error", [MailcowAPIError("HTTP error 500"), MailcowConnectionError("down")]
)
async def test_unreachable_server_retries_later(
    hass: HomeAssistant, mailcow_api: MagicMock, error
) -> None:
    mailcow_api.get_status_version.side_effect = error
    entry = make_entry()
    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_RETRY


# --- migration -------------------------------------------------------------------------


def _legacy(data=None, options=None, unique_id=None, version=1) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Mailcow",
        data=data if data is not None else {CONF_BASE_URL: "mail.example.com/"},
        options=options if options is not None else {CONF_API_KEY: "old-key"},
        unique_id=unique_id,
        version=version,
    )


async def test_migration_from_version_1(hass: HomeAssistant) -> None:
    entry = _legacy()
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 2
    assert entry.data == {
        CONF_BASE_URL: "https://mail.example.com",
        CONF_API_KEY: "old-key",
        CONF_VERIFY_SSL: True,
    }
    assert entry.options == {}  # the key left the options
    assert entry.unique_id == "https://mail.example.com"


async def test_migration_lowercases_the_unique_id(hass: HomeAssistant) -> None:
    entry = _legacy(data={CONF_BASE_URL: "HTTPS://Mail.Example.COM"})
    entry.add_to_hass(hass)

    await async_migrate_entry(hass, entry)

    assert entry.unique_id == "https://mail.example.com"


async def test_migration_keeps_an_existing_unique_id(hass: HomeAssistant) -> None:
    entry = _legacy(unique_id="custom-id")
    entry.add_to_hass(hass)

    await async_migrate_entry(hass, entry)

    assert entry.unique_id == "custom-id"


async def test_migration_does_not_reuse_a_taken_unique_id(hass: HomeAssistant) -> None:
    other = make_entry()  # already owns "https://mail.example.com"
    other.add_to_hass(hass)
    entry = _legacy()
    entry.add_to_hass(hass)

    await async_migrate_entry(hass, entry)

    assert entry.version == 2
    assert entry.unique_id is None
    assert entry.data[CONF_BASE_URL] == "https://mail.example.com"


async def test_migration_keeps_an_invalid_url(hass: HomeAssistant) -> None:
    entry = _legacy(data={CONF_BASE_URL: "ftp://mail.example.com"})
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 2
    assert entry.data[CONF_BASE_URL] == "ftp://mail.example.com"
    assert entry.data[CONF_VERIFY_SSL] is True
    assert entry.unique_id is None


async def test_migration_keeps_the_api_key_stored_in_data(hass: HomeAssistant) -> None:
    entry = _legacy(
        data={CONF_BASE_URL: "mail.example.com", CONF_API_KEY: "data-key"}, options={}
    )
    entry.add_to_hass(hass)

    await async_migrate_entry(hass, entry)

    assert entry.data[CONF_API_KEY] == "data-key"


async def test_migration_prefers_the_api_key_of_the_options(hass: HomeAssistant) -> None:
    entry = _legacy(
        data={CONF_BASE_URL: "mail.example.com", CONF_API_KEY: "data-key"},
        options={CONF_API_KEY: "options-key"},
    )
    entry.add_to_hass(hass)

    await async_migrate_entry(hass, entry)

    assert entry.data[CONF_API_KEY] == "options-key"
    assert CONF_API_KEY not in entry.options


async def test_migration_keeps_other_options_and_an_existing_tls_choice(
    hass: HomeAssistant,
) -> None:
    entry = _legacy(
        data={CONF_BASE_URL: "mail.example.com", CONF_VERIFY_SSL: False},
        options={CONF_API_KEY: "k", "scan_interval": 20},
    )
    entry.add_to_hass(hass)

    await async_migrate_entry(hass, entry)

    assert entry.data[CONF_VERIFY_SSL] is False
    assert entry.options == {"scan_interval": 20}


async def test_migration_without_url_or_key(hass: HomeAssistant) -> None:
    entry = _legacy(data={}, options={})
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 2
    assert entry.data == {CONF_VERIFY_SSL: True}
    assert entry.unique_id is None


async def test_migration_leaves_a_current_entry_unchanged(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    before = dict(entry.data)

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 2
    assert dict(entry.data) == before


async def test_migration_refuses_a_newer_version(hass: HomeAssistant) -> None:
    entry = _legacy(version=3)
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is False
