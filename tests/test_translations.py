"""Consistency of the translation files, the manifest and the code."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.mailcow_ha_custom.const import DOMAIN, PLATFORMS
from custom_components.mailcow_ha_custom.sensor import SENSOR_TYPES

INTEGRATION = Path(__file__).parent.parent / "custom_components" / DOMAIN


def _load(relative: str) -> dict:
    return json.loads((INTEGRATION / relative).read_text(encoding="utf-8"))


def _keys(data: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in data.items():
        keys.add(f"{prefix}{key}")
        if isinstance(value, dict):
            keys |= _keys(value, f"{prefix}{key}.")
    return keys


STRINGS = _load("strings.json")


@pytest.mark.parametrize("language", ["en", "fr"])
def test_translations_have_the_same_keys_as_strings(language):
    translation = _load(f"translations/{language}.json")
    assert _keys(STRINGS) == _keys(translation)


@pytest.mark.parametrize("error", ["cannot_connect", "invalid_auth", "invalid_url", "ssl_error", "unknown"])
def test_config_flow_errors_are_translated(error):
    assert error in STRINGS["config"]["error"]


@pytest.mark.parametrize("reason", ["already_configured", "reauth_successful", "reconfigure_successful"])
def test_abort_reasons_are_translated(reason):
    assert reason in STRINGS["config"]["abort"]


@pytest.mark.parametrize("step", ["user", "reauth_confirm", "reconfigure"])
def test_config_steps_are_translated(step):
    assert step in STRINGS["config"]["step"]


def test_options_step_is_translated():
    assert "init" in STRINGS["options"]["step"]


def test_every_sensor_has_a_translated_name():
    for description in SENSOR_TYPES:
        assert description.translation_key in STRINGS["entity"]["sensor"]


def test_update_entity_has_a_translated_name():
    assert "update" in STRINGS["entity"]["update"]


def test_manifest_matches_the_code():
    manifest = _load("manifest.json")
    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    assert manifest["integration_type"] == "service"
    assert manifest["iot_class"] == "local_polling"


def test_platforms_match_the_files():
    for platform in PLATFORMS:
        assert (INTEGRATION / f"{platform}.py").is_file()
