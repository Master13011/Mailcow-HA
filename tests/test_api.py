"""Tests for the Mailcow API client (no network, fake session)."""

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


@pytest.mark.parametrize("status", [401, 403])
async def test_auth_errors_are_preserved(status):
    api, _ = make_api(FakeResponse(status))
    with pytest.raises(MailcowAuthenticationError):
        await api.get_status_version()


@pytest.mark.parametrize("status", [404, 500, 503])
async def test_http_errors_are_api_errors(status):
    api, _ = make_api(FakeResponse(status))
    with pytest.raises(MailcowAPIError) as err:
        await api.get_status_version()
    assert not isinstance(err.value, (MailcowAuthenticationError, MailcowConnectionError))
    assert str(status) in str(err.value)


async def test_invalid_json():
    api, _ = make_api(FakeResponse(200, json_error=True))
    with pytest.raises(MailcowAPIError):
        await api.get_status_version()


async def test_error_payload_with_auth_message():
    api, _ = make_api(FakeResponse(200, {"type": "error", "msg": "authentication failed"}))
    with pytest.raises(MailcowAuthenticationError):
        await api.get_status_version()


async def test_error_payload_generic():
    api, _ = make_api(FakeResponse(200, {"type": "error", "msg": "boom"}))
    with pytest.raises(MailcowAPIError):
        await api.get_status_version()


async def test_timeout_and_connection_errors():
    api, _ = make_api(error=TimeoutError())
    with pytest.raises(MailcowConnectionError):
        await api.get_status_version()
    api, _ = make_api(error=ClientError())
    with pytest.raises(MailcowConnectionError):
        await api.get_status_version()


async def test_ssl_error():
    api, _ = make_api(error=ClientSSLError(MagicMock(), OSError("ssl")))
    with pytest.raises(MailcowSSLError):
        await api.get_status_version()


async def test_success_and_url_building():
    api, session = make_api(FakeResponse(200, {"version": "2025-03a"}))
    assert await api.get_status_version() == "2025-03a"
    url, kwargs = session.calls[0]
    assert url == "https://mail.example.com/api/v1/get/status/version"
    assert kwargs["headers"]["X-API-Key"] == "k"


async def test_counts_and_shapes():
    api, _ = make_api(FakeResponse(200, [1, 2, 3]))
    assert await api.get_mailbox_count() == 3
    api, _ = make_api(FakeResponse(200, {}))
    assert await api.get_domain_count() is None
    api, _ = make_api(FakeResponse(200, "x"))
    assert await api.get_status_containers() == []


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


# --- additional API tests --------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "endpoint"),
    [
        ("get_status_version", "status/version"),
        ("get_mailbox_count", "mailbox/all"),
        ("get_domain_count", "domain/all"),
        ("get_status_vmail", "status/vmail"),
        ("get_status_containers", "status/containers"),
    ],
)
async def test_each_method_calls_its_endpoint(method, endpoint):
    api, session = make_api(FakeResponse(200, {}))
    await getattr(api, method)()
    assert len(session.calls) == 1
    assert session.calls[0][0] == f"https://mail.example.com/api/v1/get/{endpoint}"


async def test_request_headers_and_timeout():
    api, session = make_api(FakeResponse(200, {"version": "2025-03"}))
    await api.get_status_version()
    _, kwargs = session.calls[0]
    assert kwargs["headers"] == {"X-API-Key": "k", "Accept": "application/json"}
    assert kwargs["timeout"].total == 15


def test_base_url_property_is_normalized():
    api, _ = make_api()
    assert api.base_url == "https://mail.example.com"


def test_invalid_url_is_refused_at_construction():
    with pytest.raises(MailcowInvalidURLError):
        MailcowAPI({"base_url": "ftp://example.com", "api_key": "k"}, FakeSession())


async def test_error_payload_with_denied_message():
    api, _ = make_api(FakeResponse(200, {"type": "error", "msg": "Access DENIED"}))
    with pytest.raises(MailcowAuthenticationError):
        await api.get_status_version()


async def test_error_payload_without_message():
    api, _ = make_api(FakeResponse(200, {"type": "error"}))
    with pytest.raises(MailcowAPIError) as err:
        await api.get_status_version()
    assert not isinstance(err.value, MailcowAuthenticationError)


async def test_version_shapes():
    api, _ = make_api(FakeResponse(200, ["2025-03"]))
    assert await api.get_status_version() is None
    api, _ = make_api(FakeResponse(200, {"other": 1}))
    assert await api.get_status_version() is None


async def test_counts_for_an_empty_list():
    api, _ = make_api(FakeResponse(200, []))
    assert await api.get_mailbox_count() == 0
    assert await api.get_domain_count() == 0


async def test_vmail_shapes():
    status = {"used_percent": "55%", "disk": "/dev/sda1"}
    api, _ = make_api(FakeResponse(200, status))
    assert await api.get_status_vmail() == status
    api, _ = make_api(FakeResponse(200, ["x"]))
    assert await api.get_status_vmail() == {}


async def test_containers_shapes_are_returned_unchanged():
    as_dict = {"nginx": {"state": "running"}}
    as_list = [{"container": "nginx", "state": "running"}]
    api, _ = make_api(FakeResponse(200, as_dict))
    assert await api.get_status_containers() == as_dict
    api, _ = make_api(FakeResponse(200, as_list))
    assert await api.get_status_containers() == as_list
