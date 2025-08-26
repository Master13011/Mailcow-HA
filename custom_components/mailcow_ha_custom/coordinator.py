from datetime import timedelta
import logging
from homeassistant.util import dt as dt_util
from typing import Any
import aiohttp
from aiohttp import ClientTimeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

async def is_night_time(hass) -> bool:
    tz = await dt_util.async_get_time_zone(str(hass.config.time_zone))
    now = dt_util.now(tz)  # aware
    return now.hour >= 23 or now.hour < 5

class MailcowCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        hass,
        api,
        scan_interval: int,
        disable_check_at_night: bool,
        entry_id: str,
        base_url: str,
        session: aiohttp.ClientSession,
    ):
        super().__init__(
            hass,
            _LOGGER,
            name="Mailcow Coordinator",
            update_interval=timedelta(minutes=scan_interval),
        )
        self.api = api
        self.disable_check_at_night = disable_check_at_night
        self.entry_id = entry_id
        self._base_url = base_url
        self._cached_latest_version: str | None = None
        self._session = session

    async def _fetch_latest_github_version(self) -> str:
        github_url = "https://api.github.com/repos/mailcow/mailcow-dockerized/tags"
        try:
            timeout = ClientTimeout(total=10)
            async with self._session.get(github_url, timeout=timeout) as response:
                if response.status == 200:
                    tags = await response.json()
                    if tags:
                        sorted_tags = sorted(tags, key=lambda x: x["name"], reverse=True)
                        return sorted_tags[0].get("name", "unknown")
        except Exception as e:
            _LOGGER.error(f"Error fetching GitHub version: {e}")
        return "unknown"

    async def _async_update_data(self) -> dict[str, Any]:
        if self.disable_check_at_night and await is_night_time(self.hass):
            _LOGGER.debug("Night check disabled; skipping data update.")
            return self.data or {}
        try:
            version = await self.api.get_status_version()
            mailbox_count = await self.api.get_mailbox_count()
            domain_count = await self.api.get_domain_count()
            vmail_status = await self.api.get_status_vmail()
            containers_status = await self.api.get_status_containers()
            latest_version = await self._fetch_latest_github_version()

            return {
                "version": version,
                "mailbox_count": mailbox_count,
                "domain_count": domain_count,
                "vmail_status": vmail_status,
                "containers_status": containers_status,
                "latest_version": latest_version,
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
