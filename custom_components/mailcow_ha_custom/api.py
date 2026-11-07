"""API client for Mailcow."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from aiohttp import ClientError, ClientSession, ClientSSLError, ClientTimeout

from .const import CONF_API_KEY, CONF_BASE_URL
from .exceptions import (
    MailcowAPIError,
    MailcowAuthenticationError,
    MailcowConnectionError,
    MailcowInvalidURLError,
    MailcowSSLError,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15


def normalize_base_url(raw: str) -> str:
    """Return a clean base URL (scheme added if missing, no trailing slash).

    Raises MailcowInvalidURLError if the value cannot be used.
    """
    value = (raw or "").strip()
    if not value:
        raise MailcowInvalidURLError("Empty URL")
    if "://" not in value:
        value = f"https://{value}"
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise MailcowInvalidURLError("Invalid URL")
    try:
        _ = parts.port  # raises ValueError for an invalid port
    except ValueError as err:
        raise MailcowInvalidURLError("Invalid port") from err
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


class MailcowAPI:
    """Asynchronous Mailcow API client."""

    def __init__(self, config_data: dict[str, Any], session: ClientSession) -> None:
        self._base_url = normalize_base_url(config_data[CONF_BASE_URL])
        self._api_key = config_data[CONF_API_KEY]
        self._session = session

    @property
    def base_url(self) -> str:
        """Return the normalized base URL."""
        return self._base_url

    async def _get(self, endpoint: str) -> Any:
        """Generic GET request to the Mailcow API."""
        url = f"{self._base_url}/api/v1/get/{endpoint}"
        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}
        timeout = ClientTimeout(total=REQUEST_TIMEOUT)

        try:
            async with self._session.get(
                url, headers=headers, timeout=timeout
            ) as response:
                status = response.status
                if status in (401, 403):
                    raise MailcowAuthenticationError(
                        "Invalid API key or permission denied"
                    )
                if status >= 400:
                    body = await response.text()
                    _LOGGER.debug("HTTP %s from %s: %.200s", status, url, body)
                    raise MailcowAPIError(f"HTTP error {status}")
                try:
                    data = await response.json(content_type=None)
                except (ValueError, ClientError) as err:
                    raise MailcowAPIError("Invalid JSON response") from err
        except MailcowAPIError:
            # Our own errors must not be swallowed by the handlers below.
            raise
        except TimeoutError as err:
            raise MailcowConnectionError("Connection timed out") from err
        except ClientSSLError as err:
            raise MailcowSSLError("TLS certificate verification failed") from err
        except ClientError as err:
            raise MailcowConnectionError("Failed to connect to Mailcow API") from err

        # Some Mailcow versions answer HTTP 200 with an error payload.
        if isinstance(data, dict) and data.get("type") == "error":
            message = str(data.get("msg", "")).lower()
            if "authentication" in message or "denied" in message:
                raise MailcowAuthenticationError("Invalid API key or permission denied")
            raise MailcowAPIError("Mailcow API returned an error")
        return data

    async def get_mailbox_count(self) -> int | None:
        data = await self._get("mailbox/all")
        return len(data) if isinstance(data, list) else None

    async def get_domain_count(self) -> int | None:
        data = await self._get("domain/all")
        return len(data) if isinstance(data, list) else None

    async def get_status_version(self) -> str | None:
        data = await self._get("status/version")
        return data.get("version") if isinstance(data, dict) else None

    async def get_status_vmail(self) -> dict[str, Any]:
        result = await self._get("status/vmail")
        return result if isinstance(result, dict) else {}

    async def get_status_containers(self) -> list[Any] | dict[Any, Any]:
        result = await self._get("status/containers")
        return result if isinstance(result, (list, dict)) else []
