"""Helpers shared by the Mailcow tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.mailcow_ha_custom.const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.mailcow_ha_custom.util import sanitize_url

BASE_URL = "https://mail.example.com"
API_KEY = "secret-key"

PATCH_API = "custom_components.mailcow_ha_custom.MailcowAPI"
PATCH_LATEST = (
    "custom_components.mailcow_ha_custom.coordinator"
    ".MailcowCoordinator._fetch_latest_github_version"
)

VMAIL = {
    "type": "info",
    "disk": "/dev/sda1",
    "used": "5G",
    "total": "10G",
    "used_percent": "55%",
}

CONTAINERS = {
    "nginx-mailcow": {"container": "nginx-mailcow", "state": "running"},
    "postfix-mailcow": {"container": "postfix-mailcow", "state": "running"},
}


def make_entry(options: dict[str, Any] | None = None, **data: Any) -> MockConfigEntry:
    """Return a Mailcow config entry (version 2) for ``BASE_URL``."""
    entry_data: dict[str, Any] = {
        CONF_BASE_URL: BASE_URL,
        CONF_API_KEY: API_KEY,
        CONF_VERIFY_SSL: True,
    }
    entry_data.update(data)
    return MockConfigEntry(
        domain=DOMAIN,
        title="Mailcow",
        data=entry_data,
        options=options or {},
        unique_id=BASE_URL,
        version=2,
    )


def make_api(
    *,
    version: Any = "2025-03a",
    mailbox_count: Any = 3,
    domain_count: Any = 2,
    vmail: Any = None,
    containers: Any = None,
) -> MagicMock:
    """Return a fake ``MailcowAPI`` answering like a healthy server."""
    api = MagicMock()
    api.base_url = BASE_URL
    api.get_status_version = AsyncMock(return_value=version)
    api.get_mailbox_count = AsyncMock(return_value=mailbox_count)
    api.get_domain_count = AsyncMock(return_value=domain_count)
    api.get_status_vmail = AsyncMock(return_value=VMAIL if vmail is None else vmail)
    api.get_status_containers = AsyncMock(
        return_value=CONTAINERS if containers is None else containers
    )
    return api


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add the entry to Home Assistant and set it up."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def unique_id(entry: MockConfigEntry, key: str) -> str:
    """Return the unique id of an entity of ``entry`` (format kept since v1)."""
    return f"mailcow_{key}_{sanitize_url(BASE_URL)}_{entry.entry_id}"


class FakeResponse:
    """Minimal stand-in for an aiohttp response (GitHub lookups)."""

    def __init__(self, status: int = 200, payload: Any = None, error: Exception | None = None):
        self.status = status
        self._payload = payload
        self._error = error

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *exc: Any) -> bool:
        return False

    async def json(self, **kwargs: Any) -> Any:
        if self._error:
            raise self._error
        return self._payload


class _Context:
    def __init__(self, item: FakeResponse | Exception) -> None:
        self._item = item

    async def __aenter__(self) -> FakeResponse:
        if isinstance(self._item, Exception):
            raise self._item
        return self._item

    async def __aexit__(self, *exc: Any) -> bool:
        return False


class FakeGithubSession:
    """Fake session answering per URL (404 when a URL has no route)."""

    def __init__(self, routes: dict[str, FakeResponse | Exception] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> _Context:
        self.calls.append((url, kwargs))
        return _Context(self.routes.get(url, FakeResponse(404)))
