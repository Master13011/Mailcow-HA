from datetime import timedelta, datetime
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

   
def is_night_time(now: datetime, start: int, end: int) -> bool:
    hour = now.hour
    return hour >= start or hour < end if start > end else start <= hour < end
    
class MailcowCoordinator(DataUpdateCoordinator):
    def __init__(
        self,
        *,
        hass,
        api,
        scan_interval: int,
        disable_check_at_night: bool,
        night_start_hour: int,
        night_end_hour: int,
        entry_id: str,
        base_url: str,
        session,
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
        self._cached_latest_version = None
        self._session = session
        self.night_start_hour = night_start_hour
        self.night_end_hour = night_end_hour

    async def _fetch_latest_github_version(self):
        import aiohttp
        github_url = "https://api.github.com/repos/mailcow/mailcow-dockerized/tags"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(github_url) as response:
                    if response.status == 200:
                        tags = await response.json()
                        if tags:
                            sorted_tags = sorted(tags, key=lambda x: x["name"], reverse=True)
                            return sorted_tags[0]["name"]
        except Exception as e:
            _LOGGER.error(f"Error fetching GitHub version: {e}")
        return "unknown"

    async def _async_update_data(self):
        if self.disable_check_at_night and is_night_time(datetime.now(), self.night_start_hour, self.night_end_hour):
            _LOGGER.debug("Night check disabled; skipping data update.")
            return self.data or {}
        try:
            version = await self.api.get_status_version()
            mailbox_count = await self.api.get_mailbox_count()
            domain_count = await self.api.get_domain_count()
            vmail_status = await self.api.get_status_vmail()
            containers_status = await self.api.get_status_containers()

            if not self._cached_latest_version:
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
            raise UpdateFailed(f"Error fetching data: {err}")
