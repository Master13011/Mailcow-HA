from datetime import timedelta, datetime
import pytz
import logging
from typing import Any
import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

def is_night_time(hass) -> bool:
    """Retourne True si l'heure locale Home Assistant est entre 23h et 5h."""
    # Récupère le fuseau horaire configuré dans Home Assistant
    tz_name = str(hass.config.time_zone)
    tz = pytz.timezone(tz_name)
    now = datetime.now(tz)
    hour = now.hour
    return hour >= 23 or hour < 5

class MailcowCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, scan_interval: int, disable_check_at_night: bool, entry_id: str, base_url: str, session: aiohttp.ClientSession,):
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
            async with self._session.get(github_url, timeout=10) as response:
                if response.status == 200:
                    tags = await response.json()
                    if tags:
                        sorted_tags = sorted(tags, key=lambda x: x["name"], reverse=True)
                        return sorted_tags[0].get("name", "unknown")
        except Exception as e:
            _LOGGER.error(f"Error fetching GitHub version: {e}")
        return "unknown"

    async def _async_update_data(self) -> dict[str, Any]:
        if self.disable_check_at_night and is_night_time():
            _LOGGER.debug("Night check disabled; skipping data update.")
            return self.data or {}
        try:
            version = await self.api.get_status_version()
            mailbox_count = await self.api.get_mailbox_count()
            domain_count = await self.api.get_domain_count()
            vmail_status = await self.api.get_status_vmail()
            containers_status = await self.api.get_status_containers()

            if self._cached_latest_version is None:
                self._cached_latest_version = await self._fetch_latest_github_version()

            return {
                "version": version,
                "mailbox_count": mailbox_count,
                "domain_count": domain_count,
                "vmail_status": vmail_status,
                "containers_status": containers_status,
                "latest_version": self._cached_latest_version,
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
