"""Tests of the coordinator: polling, night pause, errors and GitHub lookup."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.mailcow_ha_custom.const import (
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
    GITHUB_LATEST_RELEASE_URL,
    GITHUB_TAGS_URL,
    LATEST_VERSION_RETRY,
    LATEST_VERSION_TTL,
)
from custom_components.mailcow_ha_custom.coordinator import MailcowCoordinator
from custom_components.mailcow_ha_custom.exceptions import (
    MailcowAPIError,
    MailcowAuthenticationError,
    MailcowConnectionError,
)

from .common import (
    BASE_URL,
    CONTAINERS,
    VMAIL,
    FakeGithubSession,
    FakeResponse,
    make_api,
    make_entry,
)

COORDINATOR = "custom_components.mailcow_ha_custom.coordinator"
PREVIOUS = {"version": "old", "latest_version": "old"}


def _coordinator(
    hass: HomeAssistant, options=None, api=None, github=None
) -> MailcowCoordinator:
    entry = make_entry(options=options)
    entry.add_to_hass(hass)
    return MailcowCoordinator(
        hass,
        entry,
        api or make_api(),
        github or FakeGithubSession(),
    )


def _release(tag: str) -> FakeResponse:
    return FakeResponse(200, {"tag_name": tag})


def _tags(*names: str) -> FakeResponse:
    return FakeResponse(200, [{"name": name} for name in names])


# --- construction ----------------------------------------------------------------


async def test_default_settings(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass)
    assert coordinator.update_interval == timedelta(minutes=10)
    assert coordinator.disable_check_at_night is False
    assert coordinator.base_url == BASE_URL


@pytest.mark.parametrize(
    ("value", "minutes"),
    [
        (5, 5),
        (5.0, 5),
        ("30", 30),
        (1, 1),
        (1440, 1440),
        (0, 1),  # never a 0-minute interval
        (-5, 1),
        ("abc", 10),  # invalid value: default interval
        (None, 10),
    ],
)
async def test_scan_interval_from_options(hass: HomeAssistant, value, minutes) -> None:
    coordinator = _coordinator(hass, {CONF_SCAN_INTERVAL: value})
    assert coordinator.update_interval == timedelta(minutes=minutes)


async def test_night_pause_option(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass, {CONF_DISABLE_CHECK_AT_NIGHT: True})
    assert coordinator.disable_check_at_night is True


# --- update ----------------------------------------------------------------------


async def test_update_returns_all_values(hass: HomeAssistant) -> None:
    github = FakeGithubSession({GITHUB_LATEST_RELEASE_URL: _release("2025-04")})
    coordinator = _coordinator(hass, github=github)

    data = await coordinator._async_update_data()

    assert data == {
        "version": "2025-03a",
        "mailbox_count": 3,
        "domain_count": 2,
        "vmail_status": VMAIL,
        "containers_status": CONTAINERS,
        "latest_version": "2025-04",
    }


async def test_update_calls_every_endpoint_once(hass: HomeAssistant) -> None:
    api = make_api()
    coordinator = _coordinator(hass, api=api)

    await coordinator._async_update_data()

    api.get_status_version.assert_awaited_once()
    api.get_mailbox_count.assert_awaited_once()
    api.get_domain_count.assert_awaited_once()
    api.get_status_vmail.assert_awaited_once()
    api.get_status_containers.assert_awaited_once()


async def test_github_failure_does_not_break_the_update(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass, github=FakeGithubSession())  # every URL: 404

    data = await coordinator._async_update_data()

    assert data["version"] == "2025-03a"
    assert data["latest_version"] is None


# --- errors ----------------------------------------------------------------------


async def test_authentication_error_asks_for_reauthentication(hass: HomeAssistant) -> None:
    api = make_api()
    api.get_status_version.side_effect = MailcowAuthenticationError("bad key")
    coordinator = _coordinator(hass, api=api)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_authentication_error_wins_over_other_errors(hass: HomeAssistant) -> None:
    api = make_api()
    api.get_status_version.side_effect = MailcowConnectionError("down")
    api.get_domain_count.side_effect = MailcowAuthenticationError("bad key")
    coordinator = _coordinator(hass, api=api)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


@pytest.mark.parametrize(
    "error",
    [MailcowAPIError("HTTP error 500"), MailcowConnectionError("down"), RuntimeError("boom")],
)
async def test_other_errors_fail_the_update(hass: HomeAssistant, error) -> None:
    api = make_api()
    api.get_status_containers.side_effect = error
    coordinator = _coordinator(hass, api=api)

    with pytest.raises(UpdateFailed, match="Error fetching data"):
        await coordinator._async_update_data()


async def test_github_is_not_queried_when_mailcow_fails(hass: HomeAssistant) -> None:
    api = make_api()
    api.get_status_version.side_effect = MailcowConnectionError("down")
    github = FakeGithubSession()
    coordinator = _coordinator(hass, api=api, github=github)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert github.calls == []


# --- night pause -----------------------------------------------------------------


def _at(hour: int):
    return patch(f"{COORDINATOR}.dt_util.now", return_value=datetime(2026, 11, 10, hour, 30))


@pytest.mark.parametrize("hour", [23, 0, 3, 4])
async def test_night_pause_skips_the_update(hass: HomeAssistant, hour) -> None:
    api = make_api()
    coordinator = _coordinator(hass, {CONF_DISABLE_CHECK_AT_NIGHT: True}, api=api)
    coordinator.data = PREVIOUS

    with _at(hour):
        data = await coordinator._async_update_data()

    assert data is PREVIOUS  # previous values are kept
    api.get_status_version.assert_not_awaited()


@pytest.mark.parametrize("hour", [5, 12, 22])
async def test_update_runs_outside_the_night_window(hass: HomeAssistant, hour) -> None:
    api = make_api()
    coordinator = _coordinator(hass, {CONF_DISABLE_CHECK_AT_NIGHT: True}, api=api)
    coordinator.data = PREVIOUS

    with _at(hour):
        data = await coordinator._async_update_data()

    assert data["version"] == "2025-03a"
    api.get_status_version.assert_awaited_once()


async def test_first_refresh_runs_even_at_night(hass: HomeAssistant) -> None:
    api = make_api()
    coordinator = _coordinator(hass, {CONF_DISABLE_CHECK_AT_NIGHT: True}, api=api)
    assert coordinator.data is None

    with _at(2):
        data = await coordinator._async_update_data()

    assert data["version"] == "2025-03a"


async def test_update_runs_at_night_when_the_pause_is_disabled(hass: HomeAssistant) -> None:
    api = make_api()
    coordinator = _coordinator(hass, {CONF_DISABLE_CHECK_AT_NIGHT: False}, api=api)
    coordinator.data = PREVIOUS

    with _at(2):
        data = await coordinator._async_update_data()

    assert data["version"] == "2025-03a"


# --- latest version on GitHub ----------------------------------------------------


async def test_latest_release_tag_is_used(hass: HomeAssistant) -> None:
    github = FakeGithubSession({GITHUB_LATEST_RELEASE_URL: _release("2025-04")})
    coordinator = _coordinator(hass, github=github)

    assert await coordinator._fetch_latest_github_version() == "2025-04"
    assert [url for url, _ in github.calls] == [GITHUB_LATEST_RELEASE_URL]


async def test_github_request_headers_and_timeout(hass: HomeAssistant) -> None:
    github = FakeGithubSession({GITHUB_LATEST_RELEASE_URL: _release("2025-04")})
    coordinator = _coordinator(hass, github=github)

    await coordinator._fetch_latest_github_version()

    _, kwargs = github.calls[0]
    assert kwargs["headers"] == {"Accept": "application/vnd.github+json"}
    assert kwargs["timeout"].total == 10


@pytest.mark.parametrize(
    "release",
    [
        FakeResponse(404),
        FakeResponse(200, {}),  # no tag_name
        FakeResponse(200, {"tag_name": ""}),
        FakeResponse(200, {"tag_name": 2025}),
        FakeResponse(200, ["2025-04"]),  # not a dict
    ],
)
async def test_tags_are_used_when_the_release_is_unusable(hass: HomeAssistant, release) -> None:
    github = FakeGithubSession(
        {
            GITHUB_LATEST_RELEASE_URL: release,
            GITHUB_TAGS_URL: _tags("2025-03", "2025-03a", "nightly"),
        }
    )
    coordinator = _coordinator(hass, github=github)

    assert await coordinator._fetch_latest_github_version() == "2025-03a"
    assert [url for url, _ in github.calls] == [GITHUB_LATEST_RELEASE_URL, GITHUB_TAGS_URL]


async def test_no_version_when_both_sources_fail(hass: HomeAssistant) -> None:
    github = FakeGithubSession(
        {GITHUB_LATEST_RELEASE_URL: FakeResponse(500), GITHUB_TAGS_URL: FakeResponse(500)}
    )
    coordinator = _coordinator(hass, github=github)

    assert await coordinator._fetch_latest_github_version() is None


async def test_no_version_when_tags_are_unusable(hass: HomeAssistant) -> None:
    github = FakeGithubSession({GITHUB_TAGS_URL: _tags("nightly", "latest")})
    coordinator = _coordinator(hass, github=github)

    assert await coordinator._fetch_latest_github_version() is None


@pytest.mark.parametrize("error", [ClientError("boom"), TimeoutError(), ValueError("bad json")])
async def test_github_errors_give_no_version(hass: HomeAssistant, error) -> None:
    github = FakeGithubSession({GITHUB_LATEST_RELEASE_URL: error, GITHUB_TAGS_URL: error})
    coordinator = _coordinator(hass, github=github)

    assert await coordinator._fetch_latest_github_version() is None


async def test_invalid_json_from_github_gives_no_version(hass: HomeAssistant) -> None:
    broken = FakeResponse(200, error=ValueError("bad json"))
    github = FakeGithubSession({GITHUB_LATEST_RELEASE_URL: broken})
    coordinator = _coordinator(hass, github=github)

    assert await coordinator._fetch_latest_github_version() is None


# --- cache of the latest version -----------------------------------------------------


def _with_fetch(coordinator: MailcowCoordinator, *results) -> AsyncMock:
    fetch = AsyncMock(side_effect=list(results))
    coordinator._fetch_latest_github_version = fetch
    return fetch


async def test_latest_version_is_cached_for_six_hours(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass)
    fetch = _with_fetch(coordinator, "2025-04", "2025-05")

    with patch(f"{COORDINATOR}.time") as clock:
        clock.monotonic.return_value = 1000.0
        assert await coordinator._async_get_latest_version() == "2025-04"

        clock.monotonic.return_value = 1000.0 + LATEST_VERSION_TTL - 1
        assert await coordinator._async_get_latest_version() == "2025-04"
        assert fetch.await_count == 1

        clock.monotonic.return_value = 1000.0 + LATEST_VERSION_TTL
        assert await coordinator._async_get_latest_version() == "2025-05"
        assert fetch.await_count == 2


async def test_failed_lookup_is_retried_after_fifteen_minutes(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass)
    fetch = _with_fetch(coordinator, None, "2025-04")

    with patch(f"{COORDINATOR}.time") as clock:
        clock.monotonic.return_value = 1000.0
        assert await coordinator._async_get_latest_version() is None

        clock.monotonic.return_value = 1000.0 + LATEST_VERSION_RETRY - 1
        assert await coordinator._async_get_latest_version() is None
        assert fetch.await_count == 1

        clock.monotonic.return_value = 1000.0 + LATEST_VERSION_RETRY
        assert await coordinator._async_get_latest_version() == "2025-04"
        assert fetch.await_count == 2


async def test_previous_version_is_kept_when_a_refresh_fails(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass)
    fetch = _with_fetch(coordinator, "2025-04", None, None)

    with patch(f"{COORDINATOR}.time") as clock:
        clock.monotonic.return_value = 1000.0
        assert await coordinator._async_get_latest_version() == "2025-04"

        clock.monotonic.return_value = 1000.0 + LATEST_VERSION_TTL
        assert await coordinator._async_get_latest_version() == "2025-04"  # kept
        assert fetch.await_count == 2

        # The failure only postpones the next try by 15 minutes
        clock.monotonic.return_value = 1000.0 + LATEST_VERSION_TTL + LATEST_VERSION_RETRY - 1
        await coordinator._async_get_latest_version()
        assert fetch.await_count == 2

        clock.monotonic.return_value = 1000.0 + LATEST_VERSION_TTL + LATEST_VERSION_RETRY
        await coordinator._async_get_latest_version()
        assert fetch.await_count == 3
