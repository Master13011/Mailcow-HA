"""Tests for the pure helper functions."""

import pytest

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
    assert containers_state({"a": "x"}) == "N/A"
    assert containers_state(None) == "N/A"


def test_containers_attributes():
    assert containers_attributes({"a": {"state": "running"}}) == {"a": {"state": "running"}}
    assert containers_attributes([{"container": "a"}]) == {"a": {"container": "a"}}
    assert containers_attributes(None) == {}


def test_sanitize_url_is_stable():
    assert sanitize_url("https://mail.example.com") == "httpsmailexamplecom"


# --- additional edge cases ---------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    ["2025-3", "25-03", "2025-03ab", "2025-03A", "v2025-03", "", "2025/03", 2025, None],
)
def test_parse_version_rejects_malformed_values(value):
    assert parse_version(value) is None


def test_parse_version_ignores_surrounding_spaces():
    assert parse_version(" 2025-03a ") == (2025, 3, "a")


@pytest.mark.parametrize(
    ("latest", "installed", "expected"),
    [
        ("2025-03b", "2025-03a", True),
        ("2025-03", "2025-03a", False),  # no suffix is older than "a"
        ("2026-01", "2025-12z", True),  # a new year always wins
        ("2025-03a", "2025-03a", False),
        ("2025-03", "weird", True),  # unknown format: different means newer
        ("weird", "weird", False),
    ],
)
def test_is_newer_edge_cases(latest, installed, expected):
    assert is_newer(latest, installed) is expected


def test_latest_from_tags_skips_invalid_entries():
    tags = [None, "2025-03", {"foo": 1}, {"name": 5}, {"name": "2025-04"}]
    assert latest_from_tags(tags) == "2025-04"


def test_latest_from_tags_does_not_depend_on_the_order():
    assert latest_from_tags([{"name": "2025-03a"}, {"name": "2025-03"}]) == "2025-03a"
    assert latest_from_tags([{"name": "2025-12"}, {"name": "2026-01"}]) == "2026-01"
    assert latest_from_tags([{"name": "2026-01"}, {"name": "2025-12"}]) == "2026-01"
    assert latest_from_tags([{"name": "nightly"}]) is None


@pytest.mark.parametrize("hour", range(24))
def test_night_window_for_every_hour(hour):
    assert is_night_hour(hour) is (hour >= 23 or hour < 5)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 55 % ", 55.0),
        ("12.5%", 12.5),
        (0, 0.0),
        ("0%", 0.0),
        ("100", 100.0),
    ],
)
def test_vmail_percent_formats(raw, expected):
    assert vmail_percent({"used_percent": raw}) == expected


@pytest.mark.parametrize("status", ["55%", ["55%"], 55, {"used_percent": None}])
def test_vmail_percent_unusable_inputs(status):
    assert vmail_percent(status) is None


def test_containers_state_edge_cases():
    assert containers_state([{"state": "running"}, {"state": "exited"}]) == "Issues Detected"
    assert containers_state([{"container": "a"}]) == "Issues Detected"  # no state key
    assert containers_state([]) == "No Data"
    assert containers_state([{"state": "running"}, "oops"]) == "N/A"
    assert containers_state("running") == "N/A"


def test_containers_attributes_edge_cases():
    as_dict = {"a": {"state": "running"}}
    assert containers_attributes(as_dict) is as_dict
    assert containers_attributes([{"state": "running"}, {"state": "exited"}]) == {
        "0": {"state": "running"},
        "1": {"state": "exited"},
    }
    assert containers_attributes([{"container": "a"}, "x"]) == {
        "a": {"container": "a"},
        "1": "x",
    }
    assert containers_attributes("oops") == {}
    assert containers_attributes([]) == {}


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://192.168.1.10:8080", "http1921681108080"),
        ("https://mail.example.com/path", "httpsmailexamplecompath"),
        ("", ""),
    ],
)
def test_sanitize_url_keeps_only_alphanumeric_characters(url, expected):
    assert sanitize_url(url) == expected
