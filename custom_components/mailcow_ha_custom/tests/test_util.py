"""Tests for the pure helper functions."""

from custom_components.mailcow_ha_custom.util import (
    containers_attributes,
    containers_state,
    is_newer,
    is_night_hour,
    latest_from_tags,
    parse_version,
    sanitize_url,
    vmail_percent,
)


def test_parse_version():
    assert parse_version("2025-03") == (2025, 3, "")
    assert parse_version("2025-03a") == (2025, 3, "a")
    assert parse_version("unknown") is None
    assert parse_version(None) is None


def test_is_newer():
    assert is_newer("2025-03a", "2025-03") is True
    assert is_newer("2025-04", "2025-03b") is True
    assert is_newer("2025-12", "2026-01") is False
    assert is_newer("2025-03a", "2025-03a") is False
    # unknown format falls back to inequality
    assert is_newer("weird", "2025-03") is True


def test_latest_from_tags_ignores_non_versions():
    tags = [{"name": "2025-03"}, {"name": "2025-03a"}, {"name": "nightly"}, {"name": "1.0"}]
    assert latest_from_tags(tags) == "2025-03a"
    assert latest_from_tags([]) is None
    assert latest_from_tags("nope") is None


def test_night_hours():
    assert is_night_hour(23) and is_night_hour(0) and is_night_hour(4)
    assert not is_night_hour(5) and not is_night_hour(12) and not is_night_hour(22)


def test_vmail_percent():
    assert vmail_percent({"used_percent": "55%"}) == 55.0
    assert vmail_percent({"used_percent": 12}) == 12.0
    assert vmail_percent({"used_percent": "abc"}) is None
    assert vmail_percent({}) is None
    assert vmail_percent(None) is None


def test_containers_state():
    ok = {"a": {"state": "running"}, "b": {"state": "running"}}
    bad = {"a": {"state": "running"}, "b": {"state": "exited"}}
    assert containers_state(ok) == "All Running"
    assert containers_state(bad) == "Issues Detected"
    assert containers_state([{"state": "running"}]) == "All Running"
    assert containers_state({}) == "No Data"
    assert containers_state({"a": "x"}) == "Unknown"
    assert containers_state(None) == "Unknown"


def test_containers_attributes():
    assert containers_attributes({"a": {"state": "running"}}) == {"a": {"state": "running"}}
    assert containers_attributes([{"container": "a"}]) == {"a": {"container": "a"}}
    assert containers_attributes(None) == {}


def test_sanitize_url_is_stable():
    assert sanitize_url("https://mail.example.com") == "httpsmailexamplecom"
