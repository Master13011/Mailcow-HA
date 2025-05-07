import logging
import aiohttp
import time
import asyncio
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import MailcowAPI
from .const import DOMAIN, IS_NOT_CHECK_START_HOUR, IS_NOT_CHECK_END_HOUR

_LOGGER = logging.getLogger(__name__)


def sanitize_url(url: str) -> str:
    return ''.join(filter(str.isalnum, url))


def is_not_check(start_hour: int, end_hour: int) -> bool:
    """Returns True if the current time is within the disabled check window."""
    now = datetime.now().hour
    if start_hour <= end_hour:
        return start_hour <= now < end_hour
    else:
        # Overnight range, e.g., 23 -> 5
        return now >= start_hour or now < end_hour


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    base_url = config_entry.data["base_url"]
    api = hass.data[DOMAIN][config_entry.entry_id]
    is_not_check_start_hour = config_entry.options.get(IS_NOT_CHECK_START_HOUR, 23)
    is_not_check_end_hour = config_entry.options.get(IS_NOT_CHECK_END_HOUR, 5)

    _LOGGER.debug("Setting up Mailcow sensors.")

    sensors = [
        MailcowMailboxCountSensor(api, base_url, config_entry.entry_id, is_not_check_start_hour, is_not_check_end_hour),
        MailcowDomainCountSensor(api, base_url, config_entry.entry_id, is_not_check_start_hour, is_not_check_end_hour),
        MailcowVersionSensor(api, base_url, config_entry.entry_id, is_not_check_start_hour, is_not_check_end_hour),
        MailcowVmailStatusSensor(api, base_url, config_entry.entry_id, is_not_check_start_hour, is_not_check_end_hour),
        MailcowContainersStatusSensor(api, base_url, config_entry.entry_id, is_not_check_start_hour, is_not_check_end_hour),
        MailcowUpdateAvailableSensor(api, base_url, config_entry.entry_id, is_not_check_start_hour, is_not_check_end_hour),
    ]

    async_add_entities(sensors, True)
    _LOGGER.info(f"Added {len(sensors)} Mailcow sensors.")


class MailcowSensor(SensorEntity):
    def __init__(self, api: MailcowAPI, base_url: str, entry_id: str, skip_start_hour: int, skip_end_hour: int):
        self.api = api
        self._base_url = base_url
        self._entry_id = entry_id
        self._cache = {}
        self._cache_expiry = 43200  # 12h
        self._skip_start_hour = skip_start_hour
        self._skip_end_hour = skip_end_hour
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _get_cached_data(self, key):
        cached = self._cache.get(key)
        if cached and (cached["timestamp"] + self._cache_expiry > time.time()):
            return cached["value"]
        return None

    def _set_cache_data(self, key, value):
        self._cache[key] = {"value": value, "timestamp": time.time()}

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Mailcow",
            "manufacturer": "Mailcow",
            "model": "API",
            "sw_version": self._get_cached_data("mailcow_version") or "Unknown",
        }


class MailcowMailboxCountSensor(MailcowSensor):
    def __init__(self, api, base_url, entry_id, skip_start_hour, skip_end_hour):
        super().__init__(api, base_url, entry_id, skip_start_hour, skip_end_hour)
        self._attr_name = "Mailcow Mailbox Count"
        self._attr_unique_id = f"mailcow_mailbox_count_{sanitize_url(self._base_url)}_{self._entry_id}"
        self._attr_icon = "mdi:email-multiple"

    async def async_update(self) -> None:
        try:
            if is_not_check(self._skip_start_hour, self._skip_end_hour):
                _LOGGER.debug("Skipping mailbox count update due to time window.")
                return
            mailbox_count = self._get_cached_data("mailbox_count")
            if mailbox_count is None:
                mailbox_count = await self.api.get_mailbox_count()
                if mailbox_count is not None:
                    self._set_cache_data("mailbox_count", mailbox_count)
            self._attr_native_value = int(mailbox_count) if mailbox_count is not None else None
        except Exception as e:
            _LOGGER.error(f"Error getting mailbox count: {e}")
            self._attr_native_value = None


class MailcowDomainCountSensor(MailcowSensor):
    def __init__(self, api, base_url, entry_id, skip_start_hour, skip_end_hour):
        super().__init__(api, base_url, entry_id, skip_start_hour, skip_end_hour)
        self._attr_name = "Mailcow Domain Count"
        self._attr_unique_id = f"mailcow_domain_count_{sanitize_url(self._base_url)}_{self._entry_id}"
        self._attr_icon = "mdi:domain"

    async def async_update(self) -> None:
        try:
            if is_not_check(self._skip_start_hour, self._skip_end_hour):
                _LOGGER.debug("Skipping domain count update due to time window.")
                return
            domain_count = self._get_cached_data("domain_count")
            if domain_count is None:
                domain_count = await self.api.get_domain_count()
                if domain_count is not None:
                    self._set_cache_data("domain_count", domain_count)
            self._attr_native_value = int(domain_count) if domain_count is not None else None
        except Exception as e:
            _LOGGER.error(f"Error getting domain count: {e}")
            self._attr_native_value = None


class MailcowVersionSensor(MailcowSensor):
    def __init__(self, api, base_url, entry_id, skip_start_hour, skip_end_hour):
        super().__init__(api, base_url, entry_id, skip_start_hour, skip_end_hour)
        self._attr_name = "Mailcow Version"
        self._attr_unique_id = f"mailcow_version_{sanitize_url(self._base_url)}_{self._entry_id}"
        self._attr_icon = "mdi:package-variant"
        self._attr_state_class = None

    async def async_update(self) -> None:
        try:
            if is_not_check(self._skip_start_hour, self._skip_end_hour):
                _LOGGER.debug("Skipping version update due to time window.")
                return
            version = self._get_cached_data("mailcow_version")
            if version is None:
                version = await self.api.get_status_version()
                if version is not None:
                    self._set_cache_data("mailcow_version", version)
            if version is not None:
                self._attr_native_value = str(version)
                self._attr_extra_state_attributes = {"version": version}
            else:
                self._attr_native_value = None
        except Exception as e:
            _LOGGER.error(f"Error getting Mailcow version: {e}")
            self._attr_native_value = None


class MailcowVmailStatusSensor(MailcowSensor):
    def __init__(self, api, base_url, entry_id, skip_start_hour, skip_end_hour):
        super().__init__(api, base_url, entry_id, skip_start_hour, skip_end_hour)
        self._attr_name = "Mailcow Vmail Disk Usage"
        self._attr_unique_id = f"mailcow_vmail_disk_usage_{sanitize_url(self._base_url)}_{self._entry_id}"
        self._attr_icon = "mdi:harddisk"
        self._attr_state_class = None
        self._attr_native_unit_of_measurement = "%"

    async def async_update(self) -> None:
        try:
            if is_not_check(self._skip_start_hour, self._skip_end_hour):
                _LOGGER.debug("Skipping vmail status update due to time window.")
                return
            vmail_status = self._get_cached_data("vmail_status")
            if vmail_status is None:
                vmail_status = await self.api.get_status_vmail()
                if vmail_status:
                    self._set_cache_data("vmail_status", vmail_status)
            if vmail_status:
                used_str = vmail_status.get("used_percent", "0")
                used_percent = float(used_str.rstrip('%')) if used_str.endswith('%') else float(used_str)
                self._attr_native_value = used_percent
                self._attr_extra_state_attributes = {
                    "status": "OK" if vmail_status.get("type") == "info" else "Error",
                    "disk": vmail_status.get("disk"),
                    "used": vmail_status.get("used"),
                    "total": vmail_status.get("total"),
                    "type": vmail_status.get("type")
                }
            else:
                self._attr_native_value = None
                self._attr_extra_state_attributes = {}
        except Exception as e:
            _LOGGER.error(f"Error getting vmail status: {e}")
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}


class MailcowContainersStatusSensor(MailcowSensor):
    def __init__(self, api, base_url, entry_id, skip_start_hour, skip_end_hour):
        super().__init__(api, base_url, entry_id, skip_start_hour, skip_end_hour)
        self._attr_name = "Mailcow Containers Status"
        self._attr_unique_id = f"mailcow_containers_status_{sanitize_url(self._base_url)}_{self._entry_id}"
        self._attr_icon = "mdi:docker"
        self._attr_state_class = None

    async def async_update(self) -> None:
        try:
            if is_not_check(self._skip_start_hour, self._skip_end_hour):
                _LOGGER.debug("Skipping containers status update due to time window.")
                return
            containers_status = await self.api.get_status_containers()
            if containers_status:
                all_running = all(c["state"] == "running" for c in containers_status.values())
                self._attr_native_value = "All Running" if all_running else "Issues Detected"
                self._attr_extra_state_attributes = {
                    name: {
                        "state": c["state"],
                        "started_at": c["started_at"],
                        "image": c["image"]
                    } for name, c in containers_status.items()
                }
            else:
                self._attr_native_value = "Unknown"
                self._attr_extra_state_attributes = {}
        except Exception as e:
            _LOGGER.error(f"Error getting containers status: {e}")
            self._attr_native_value = "Error"
            self._attr_extra_state_attributes = {}


class MailcowUpdateAvailableSensor(MailcowSensor):
    def __init__(self, api, base_url, entry_id, skip_start_hour, skip_end_hour, forced_version: str = None):
        super().__init__(api, base_url, entry_id, skip_start_hour, skip_end_hour)
        self._attr_name = "Mailcow Update Available"
        self._attr_unique_id = f"mailcow_update_available_{sanitize_url(self._base_url)}_{self._entry_id}"
        self._attr_icon = "mdi:package-up"
        self._attr_state_class = None
        self._forced_version = forced_version

    async def fetch_latest_github_version(self):
        github_url = "https://api.github.com/repos/mailcow/mailcow-dockerized/tags"
        retries = 3
        delay = 5
        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(github_url) as response:
                        if response.status == 200:
                            tags = await response.json()
                            if tags:
                                sorted_tags = sorted(tags, key=lambda x: x["name"], reverse=True)
                                return sorted_tags[0]["name"]
            except Exception as e:
                _LOGGER.error(f"Error fetching GitHub version (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
        return "unknown"

    async def async_update(self) -> None:
        try:
            if is_not_check(self._skip_start_hour, self._skip_end_hour):
                _LOGGER.debug("Skipping update check due to time window.")
                return

            current_version = await self.api.get_status_version()

            if self._forced_version:
                latest_version = self._forced_version
            else:
                latest_version = self._get_cached_data("latest_version")
                if not latest_version:
                    latest_version = await self.fetch_latest_github_version()
                    self._set_cache_data("latest_version", latest_version)

            update_available = (
                latest_version != current_version
                if current_version and latest_version else "Unavailable"
            )

            self._attr_native_value = "Update available" if update_available else "Up to date"
            self._attr_icon = "mdi:package-up" if update_available else "mdi:package-check"
            self._attr_extra_state_attributes = {
                "installed_version": current_version or "unknown",
                "latest_version": latest_version or "unknown",
                "release_url": "https://github.com/mailcow/mailcow-dockerized/releases"
            }

        except Exception as e:
            _LOGGER.exception(f"Error checking update availability: {e}")
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
