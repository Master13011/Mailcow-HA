"""Tests of the config flow: setup, reauthentication and reconfiguration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.mailcow_ha_custom.const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_DISABLE_CHECK_AT_NIGHT,
    CONF_SCAN_INTERVAL,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.mailcow_ha_custom.exceptions import (
    MailcowAPIError,
    MailcowAuthenticationError,
    MailcowConnectionError,
    MailcowSSLError,
)

from .common import API_KEY, BASE_URL, make_entry

CONFIG_FLOW = "custom_components.mailcow_ha_custom.config_flow"

USER_INPUT = {
    CONF_BASE_URL: "mail.example.com",
    CONF_API_KEY: "new-key",
    CONF_VERIFY_SSL: True,
}


@pytest.fixture(autouse=True)
def no_real_setup():
    """Do not set the integration up after the flow creates the entry."""
    with patch("custom_components.mailcow_ha_custom.async_setup_entry", return_value=True):
        yield


def _api(version="2025-03a", error=None) -> MagicMock:
    api = MagicMock()
    api.get_status_version = AsyncMock(return_value=version, side_effect=error)
    return api


def _suggested(result, name):
    for key in result["data_schema"].schema:
        if key == name:
            return (key.description or {}).get("suggested_value")
    raise AssertionError(f"{name} not in the form")


async def _start_user_flow(hass: HomeAssistant, user_input=None, api=None):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    with patch(f"{CONFIG_FLOW}.MailcowAPI", return_value=api or _api()) as cls:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input or USER_INPUT
        )
    return result, cls


# --- user step -----------------------------------------------------------------------


async def test_user_flow_creates_the_entry(hass: HomeAssistant) -> None:
    result, cls = await _start_user_flow(hass)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Mailcow"
    assert result["data"] == {
        CONF_BASE_URL: "https://mail.example.com",
        CONF_API_KEY: "new-key",
        CONF_VERIFY_SSL: True,
    }
    assert result["options"] == {CONF_DISABLE_CHECK_AT_NIGHT: False, CONF_SCAN_INTERVAL: 10}
    assert result["result"].unique_id == "https://mail.example.com"
    # The credentials were tried against the normalized URL
    assert cls.call_args.args[0] == {
        CONF_BASE_URL: "https://mail.example.com",
        CONF_API_KEY: "new-key",
    }


async def test_user_flow_normalizes_the_url(hass: HomeAssistant) -> None:
    result, _ = await _start_user_flow(
        hass, {**USER_INPUT, CONF_BASE_URL: "  http://Mail.Example.com:8080/  "}
    )

    assert result["data"][CONF_BASE_URL] == "http://Mail.Example.com:8080"
    assert result["result"].unique_id == "http://mail.example.com:8080"


async def test_user_flow_keeps_the_chosen_options(hass: HomeAssistant) -> None:
    result, _ = await _start_user_flow(
        hass,
        {
            **USER_INPUT,
            CONF_VERIFY_SSL: False,
            CONF_DISABLE_CHECK_AT_NIGHT: True,
            CONF_SCAN_INTERVAL: 15,
        },
    )

    assert result["data"][CONF_VERIFY_SSL] is False
    assert result["options"] == {CONF_DISABLE_CHECK_AT_NIGHT: True, CONF_SCAN_INTERVAL: 15}
    assert type(result["options"][CONF_SCAN_INTERVAL]) is int


async def test_user_flow_uses_the_tls_choice_for_the_session(hass: HomeAssistant) -> None:
    with patch(f"{CONFIG_FLOW}.async_get_clientsession") as get_session:
        await _start_user_flow(hass, {**USER_INPUT, CONF_VERIFY_SSL: False})

    assert get_session.call_args.kwargs == {"verify_ssl": False}


@pytest.mark.parametrize("raw", ["", "   ", "ftp://mail.example.com", "https://mail.example.com:99999"])
async def test_user_flow_invalid_url(hass: HomeAssistant, raw) -> None:
    result, cls = await _start_user_flow(hass, {**USER_INPUT, CONF_BASE_URL: raw})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}
    cls.assert_not_called()  # nothing is sent to an invalid address


@pytest.mark.parametrize(
    ("api", "error"),
    [
        (_api(error=MailcowAuthenticationError("bad key")), "invalid_auth"),
        (_api(error=MailcowSSLError("certificate")), "ssl_error"),
        (_api(error=MailcowConnectionError("down")), "cannot_connect"),
        (_api(error=MailcowAPIError("HTTP error 500")), "cannot_connect"),
        (_api(error=RuntimeError("boom")), "unknown"),
        (_api(version=None), "cannot_connect"),
        (_api(version=""), "cannot_connect"),
    ],
)
async def test_user_flow_errors(hass: HomeAssistant, api, error) -> None:
    result, _ = await _start_user_flow(hass, api=api)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": error}
    # What the user typed is kept in the form
    assert _suggested(result, CONF_BASE_URL) == "mail.example.com"


async def test_user_flow_recovers_after_an_error(hass: HomeAssistant) -> None:
    result, _ = await _start_user_flow(
        hass, api=_api(error=MailcowAuthenticationError("bad key"))
    )
    assert result["errors"] == {"base": "invalid_auth"}

    with patch(f"{CONFIG_FLOW}.MailcowAPI", return_value=_api()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_refuses_a_duplicate(hass: HomeAssistant) -> None:
    make_entry().add_to_hass(hass)

    result, cls = await _start_user_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    cls.assert_not_called()


async def test_user_flow_duplicate_ignores_case_and_trailing_slash(hass: HomeAssistant) -> None:
    make_entry().add_to_hass(hass)

    result, _ = await _start_user_flow(
        hass, {**USER_INPUT, CONF_BASE_URL: "HTTPS://MAIL.EXAMPLE.COM/"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_rejects_an_out_of_range_interval(hass: HomeAssistant) -> None:
    from homeassistant.data_entry_flow import InvalidData

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    for value in (0, 1441):
        with pytest.raises(InvalidData):
            await hass.config_entries.flow.async_configure(
                result["flow_id"], {**USER_INPUT, CONF_SCAN_INTERVAL: value}
            )


# --- reauthentication ------------------------------------------------------------------


async def test_reauth_updates_the_api_key(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["description_placeholders"] == {"base_url": BASE_URL}

    with patch(f"{CONFIG_FLOW}.MailcowAPI", return_value=_api()) as cls:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "fresh-key"}
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_KEY] == "fresh-key"
    assert entry.data[CONF_BASE_URL] == BASE_URL  # unchanged
    # The new key is checked against the URL of the entry
    assert cls.call_args.args[0] == {CONF_BASE_URL: BASE_URL, CONF_API_KEY: "fresh-key"}


async def test_reauth_keeps_the_tls_choice(hass: HomeAssistant) -> None:
    entry = make_entry(**{CONF_VERIFY_SSL: False})
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    with patch(f"{CONFIG_FLOW}.MailcowAPI", return_value=_api()):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "fresh-key"}
        )
    await hass.async_block_till_done()

    assert entry.data[CONF_VERIFY_SSL] is False


async def test_reauth_with_a_wrong_key_keeps_the_old_one(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    with patch(
        f"{CONFIG_FLOW}.MailcowAPI",
        return_value=_api(error=MailcowAuthenticationError("bad key")),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "wrong"}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data[CONF_API_KEY] == API_KEY


# --- reconfiguration -------------------------------------------------------------------


async def test_reconfigure_updates_key_and_tls(hass: HomeAssistant) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["description_placeholders"] == {"base_url": BASE_URL}

    with patch(f"{CONFIG_FLOW}.MailcowAPI", return_value=_api()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "fresh-key", CONF_VERIFY_SSL: False}
        )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_API_KEY] == "fresh-key"
    assert entry.data[CONF_VERIFY_SSL] is False
    assert entry.data[CONF_BASE_URL] == BASE_URL


async def test_reconfigure_shows_the_current_tls_choice(hass: HomeAssistant) -> None:
    entry = make_entry(**{CONF_VERIFY_SSL: False})
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)

    assert _suggested(result, CONF_VERIFY_SSL) is False


@pytest.mark.parametrize(
    ("error", "key"),
    [
        (MailcowSSLError("certificate"), "ssl_error"),
        (MailcowConnectionError("down"), "cannot_connect"),
        (MailcowAuthenticationError("bad key"), "invalid_auth"),
    ],
)
async def test_reconfigure_errors(hass: HomeAssistant, error, key) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    with patch(f"{CONFIG_FLOW}.MailcowAPI", return_value=_api(error=error)):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_API_KEY: "fresh-key", CONF_VERIFY_SSL: True}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": key}
    assert entry.data[CONF_API_KEY] == API_KEY
