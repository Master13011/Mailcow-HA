"""Tests of the exception hierarchy."""

import pytest

from custom_components.mailcow_ha_custom.exceptions import (
    MailcowAPIError,
    MailcowAuthenticationError,
    MailcowConnectionError,
    MailcowInvalidURLError,
    MailcowSSLError,
)


@pytest.mark.parametrize(
    "error",
    [
        MailcowAuthenticationError,
        MailcowConnectionError,
        MailcowSSLError,
        MailcowInvalidURLError,
    ],
)
def test_every_error_is_a_mailcow_api_error(error):
    assert issubclass(error, MailcowAPIError)


def test_ssl_error_is_a_connection_error():
    """The config flow relies on this order to report ssl_error before cannot_connect."""
    assert issubclass(MailcowSSLError, MailcowConnectionError)


@pytest.mark.parametrize(
    ("first", "second"),
    [
        (MailcowAuthenticationError, MailcowConnectionError),
        (MailcowAuthenticationError, MailcowInvalidURLError),
        (MailcowConnectionError, MailcowInvalidURLError),
        (MailcowConnectionError, MailcowAuthenticationError),
    ],
)
def test_error_families_do_not_overlap(first, second):
    assert not issubclass(first, second)


def test_message_is_used_as_text():
    error = MailcowAPIError("boom")
    assert str(error) == "boom"
    assert error.message == "boom"


def test_class_name_is_used_without_message():
    assert str(MailcowAPIError()) == "MailcowAPIError"
    assert str(MailcowAuthenticationError()) == "MailcowAuthenticationError"
    assert MailcowAPIError().message is None
