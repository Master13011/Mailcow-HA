"""Pure helper functions (no Home Assistant dependency, easy to unit test)."""

from __future__ import annotations

import re
from typing import Any

from .const import NIGHT_END_HOUR, NIGHT_START_HOUR

# Mailcow versions look like "2025-03", "2025-03a", "2025-12b".
_VERSION_RE = re.compile(r"^(\d{4})-(\d{2})([a-z]?)$")


def sanitize_url(url: str) -> str:
    """Keep only alphanumeric characters (used in unique IDs, do not change)."""
    return "".join(filter(str.isalnum, url))


def parse_version(version: Any) -> tuple[int, int, str] | None:
    """Parse a Mailcow version into a sortable tuple, or None if unknown."""
    if not isinstance(version, str):
        return None
    match = _VERSION_RE.match(version.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), match.group(3)


def is_newer(latest: str, installed: str) -> bool:
    """Return True if `latest` is a newer Mailcow version than `installed`."""
    parsed_latest = parse_version(latest)
    parsed_installed = parse_version(installed)
    if parsed_latest is not None and parsed_installed is not None:
        return parsed_latest > parsed_installed
    # Unknown format: fall back to "different means update available".
    return latest != installed


def latest_from_tags(tags: Any) -> str | None:
    """Pick the most recent Mailcow version from a GitHub tags payload."""
    if not isinstance(tags, list):
        return None
    versions = [
        tag["name"]
        for tag in tags
        if isinstance(tag, dict) and parse_version(tag.get("name")) is not None
    ]
    if not versions:
        return None
    return max(versions, key=lambda name: parse_version(name))  # type: ignore[arg-type,return-value]


def is_night_hour(hour: int) -> bool:
    """Return True if the hour is within the night window (23:00-05:00)."""
    return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR


def vmail_percent(vmail_status: Any) -> float | None:
    """Extract the vmail disk usage in percent, or None if unavailable."""
    if not isinstance(vmail_status, dict):
        return None
    raw = vmail_status.get("used_percent")
    if raw is None:
        return None
    try:
        return float(str(raw).strip().rstrip("%"))
    except ValueError:
        return None


def _container_items(containers: Any) -> list[Any] | None:
    if isinstance(containers, dict):
        return list(containers.values())
    if isinstance(containers, list):
        return containers
    return None


def containers_state(containers: Any) -> str:
    """Summarize the state of all Mailcow containers."""
    items = _container_items(containers)
    if items is None:
        return "N/A"
    if not items:
        return "No Data"
    if not all(isinstance(item, dict) for item in items):
        return "N/A"
    if all(item.get("state") == "running" for item in items):
        return "All Running"
    return "Issues Detected"


def containers_attributes(containers: Any) -> dict[str, Any]:
    """Return the containers as a state-attributes mapping."""
    if isinstance(containers, dict):
        return containers
    if isinstance(containers, list):
        return {
            str(item.get("container", index)) if isinstance(item, dict) else str(index): item
            for index, item in enumerate(containers)
        }
    return {}
