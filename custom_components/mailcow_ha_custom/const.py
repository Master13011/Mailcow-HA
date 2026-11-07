"""Constants for the Mailcow integration."""

DOMAIN = "mailcow_ha_custom"

CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_VERIFY_SSL = "verify_ssl"
CONF_DISABLE_CHECK_AT_NIGHT = "disable_check_at_night"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 10  # minutes
DEFAULT_VERIFY_SSL = True

# Night window during which polling can be paused (local time of Home Assistant).
NIGHT_START_HOUR = 23
NIGHT_END_HOUR = 5

# The latest Mailcow version is read from GitHub, at most every 6 hours.
# After a failure, the next attempt happens after 15 minutes.
LATEST_VERSION_TTL = 6 * 3600
LATEST_VERSION_RETRY = 15 * 60
GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/mailcow/mailcow-dockerized/releases/latest"
)
GITHUB_TAGS_URL = "https://api.github.com/repos/mailcow/mailcow-dockerized/tags"
GITHUB_RELEASES_PAGE = "https://github.com/mailcow/mailcow-dockerized/releases"

PLATFORMS = ["sensor", "update"]
