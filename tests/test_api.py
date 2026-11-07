"""Tests for the Mailcow API client (no network, fake session)."""

import asyncio
from unittest.mock import MagicMock

import pytest
from aiohttp import ClientError, ClientSSLError

from custom_components.mailcow_ha_custom.api import MailcowAPI, normalize_base_url
from custom_components.mailcow_ha_custom.exceptions import (
    MailcowAPIError,
    MailcowAuthenticationError,
    MailcowConnectionError,
    MailcowInvalidURLError,
    MailcowSSLError,
)


class FakeResponse:
    def __init__(self, status=200, payload=None, json_error=False):
        self.status = status
        self._payload = payload
        self._json_error = json_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def text(self):
        return "body"

    async def json(self, **kwargs):
        if self._json_error:
            raise ValueError("bad json")
        return self._payload


class FakeContext:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    async def __aenter__(self):
        if self._error:
            raise self._error
        return self._response

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, response=None, error=None):
        self._ctx = FakeContext(response, error)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self._ctx


def make_api(response=None, error=None):
    session = FakeSession(response, error)
    api = MailcowAPI({"base_url": "mail.example.com/", "api_key": "k"}, session)
    return api, session


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("status", [401, 403])
def test_auth_errors_are_preserved(status):
    api, _ = make_api(FakeResponse(status))
    with pytest.raises(MailcowAuthenticationError):
        run(api.get_status_version())


@pytest.mark.parametrize("status", [404, 500, 503])
def test_http_errors_are_api_errors(status):
    api, _ = make_api(FakeResponse(status))
    with pytest.raises(MailcowAPIError) as err:
        run(api.get_status_version())
    assert not isinstance(err.value, (MailcowAuthenticationError, MailcowConnectionError))
    assert str(status) in str(err.value)


def test_invalid_json():
    api, _ = make_api(FakeResponse(200, json_error=True))
    with pytest.raises(MailcowAPIError):
        run(api.get_status_version())


def test_error_payload_with_auth_message():
    api, _ = make_api(FakeResponse(200, {"type": "error", "msg": "authentication failed"}))
    with pytest.raises(MailcowAuthenticationError):
        run(api.get_status_version())


def test_error_payload_generic():
    api, _ = make_api(FakeResponse(200, {"type": "error", "msg": "boom"}))
    with pytest.raises(MailcowAPIError):
        run(api.get_status_version())


def test_timeout_and_connection_errors():
    api, _ = make_api(error=TimeoutError())
    with pytest.raises(MailcowConnectionError):
        run(api.get_status_version())
    api, _ = make_api(error=ClientError())
    with pytest.raises(MailcowConnectionError):
        run(api.get_status_version())


def test_ssl_error():
    api, _ = make_api(error=ClientSSLError(MagicMock(), OSError("ssl")))
    with pytest.raises(MailcowSSLError):
        run(api.get_status_version())


def test_success_and_url_building():
    api, session = make_api(FakeResponse(200, {"version": "2025-03a"}))
    assert run(api.get_status_version()) == "2025-03a"
    url, kwargs = session.calls[0]
    assert url == "https://mail.example.com/api/v1/get/status/version"
    assert kwargs["headers"]["X-API-Key"] == "k"


def test_counts_and_shapes():
    api, _ = make_api(FakeResponse(200, [1, 2, 3]))
    assert run(api.get_mailbox_count()) == 3
    api, _ = make_api(FakeResponse(200, {}))
    assert run(api.get_domain_count()) is None
    api, _ = make_api(FakeResponse(200, "x"))
    assert run(api.get_status_containers()) == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("mail.example.com", "https://mail.example.com"),
        ("  https://mail.example.com/ ", "https://mail.example.com"),
        ("http://192.168.1.10:8080/", "http://192.168.1.10:8080"),
        ("mail.example.com:8443", "https://mail.example.com:8443"),
        ("https://example.com/mail/?x=1#y", "https://example.com/mail"),
    ],
)
def test_normalize_base_url(raw, expected):
    assert normalize_base_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "ftp://example.com", "https://", "https://a:99999"])
def test_normalize_base_url_invalid(raw):
    with pytest.raises(MailcowInvalidURLError):
        normalize_base_url(raw)
