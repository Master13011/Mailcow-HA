"""Data update coordinator for Mailcow."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import MailcowAPI
from .const import (
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    GITHUB_LATEST_RELEASE_URL,
    GITHUB_TAGS_URL,
    LATEST_VERSION_RETRY,
    LATEST_VERSION_TTL,
)
from .exceptions import MailcowAuthenticationError
from .util import is_night_hour, latest_from_tags

_LOGGER = logging.getLogger(__name__)

type MailcowConfigEntry = ConfigEntry[MailcowCoordinator]


class MailcowCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch data from Mailcow (and the latest version from GitHub)."""

    config_entry: MailcowConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: MailcowConfigEntry,
        api: MailcowAPI,
        github_session: ClientSession,
    ) -> None:
        scan_interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="Mailcow",
            update_interval=timedelta(minutes=scan_interval),
        )
        self.api = api
        self.base_url = api.base_url
        self.disable_check_at_night: bool = config_entry.options.get(
            CONF_DISABLE_CHECK_AT_NIGHT, False
        )
        self._github_session = github_session
        self._latest_version: str | None = None
        self._next_latest_check = 0.0

    async def _fetch_latest_github_version(self) -> str | None:
        """Return the latest Mailcow version published on GitHub, or None."""
        timeout = ClientTimeout(total=10)
        headers = {"Accept": "application/vnd.github+json"}
        try:
            async with self._github_session.get(
                GITHUB_LATEST_RELEASE_URL, headers=headers, timeout=timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    tag = data.get("tag_name") if isinstance(data, dict) else None
                    if isinstance(tag, str) and tag:
                        return tag
            async with self._github_session.get(
                GITHUB_TAGS_URL, headers=headers, timeout=timeout
            ) as response:
                if response.status == 200:
                    return latest_from_tags(await response.json())
        except (ClientError, TimeoutError, ValueError) as err:
            _LOGGER.debug("Could not fetch the latest Mailcow version: %s", err)
        return None

    async def _async_get_latest_version(self) -> str | None:
        """Return the cached latest version, refreshing it when needed."""
        now = time.monotonic()
        if now >= self._next_latest_check:
            version = await self._fetch_latest_github_version()
            if version:
                self._latest_version = version
                self._next_latest_check = now + LATEST_VERSION_TTL
            else:
                # Keep the previous value and retry later (avoid GitHub rate limit).
                self._next_latest_check = now + LATEST_VERSION_RETRY
        return self._latest_version

    async def _async_update_data(self) -> dict[str, Any]:
        # Only skip when we already have data: the very first refresh always runs.
        if (
            self.disable_check_at_night
            and self.data is not None
            and is_night_hour(dt_util.now().hour)
        ):
            _LOGGER.debug("Night check disabled; skipping data update")
            return self.data

        results = await asyncio.gather(
            self.api.get_status_version(),
            self.api.get_mailbox_count(),
            self.api.get_domain_count(),
            self.api.get_status_vmail(),
            self.api.get_status_containers(),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, MailcowAuthenticationError):
                raise ConfigEntryAuthFailed(str(result)) from result
        for result in results:
            if isinstance(result, BaseException):
                raise UpdateFailed(f"Error fetching data: {result}") from result

        version, mailbox_count, domain_count, vmail_status, containers_status = results
        return {
            "version": version,
            "mailbox_count": mailbox_count,
            "domain_count": domain_count,
            "vmail_status": vmail_status,
            "containers_status": containers_status,
            "latest_version": await self._async_get_latest_version(),
        }
