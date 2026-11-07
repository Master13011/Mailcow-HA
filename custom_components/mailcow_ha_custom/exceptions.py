"""Exceptions specific to the Mailcow integration."""


class MailcowAPIError(Exception):
    """Generic error related to the Mailcow API."""

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message)
        self.message = message

    def __str__(self) -> str:
        return self.message or self.__class__.__name__


class MailcowAuthenticationError(MailcowAPIError):
    """Authentication with the Mailcow API failed (invalid key / denied)."""


class MailcowConnectionError(MailcowAPIError):
    """Connection to the Mailcow API failed (network, timeout, ...)."""


class MailcowSSLError(MailcowConnectionError):
    """The TLS certificate of the Mailcow server could not be verified."""


class MailcowInvalidURLError(MailcowAPIError):
    """The Mailcow base URL is not valid."""
