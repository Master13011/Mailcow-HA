"""API client for Mailcow."""

import logging
import asyncio
from aiohttp import ClientSession, ClientError
from .const import CONF_API_KEY, CONF_BASE_URL
from typing import Any, Optional, List, Dict, Union

_LOGGER = logging.getLogger(__name__)

from .exceptions import (
    MailcowAPIError,
    MailcowAuthenticationError,
    MailcowConnectionError
)

class MailcowAPI:
    """Asynchronous Mailcow API client."""

    def __init__(self, config_data: dict, session: ClientSession):
        self._base_url = config_data[CONF_BASE_URL].rstrip("/")
        self._api_key = config_data[CONF_API_KEY]
        self._session = session

    async def _get(self, endpoint: str) -> Any:
        """Generic GET request to Mailcow API."""
        url = f"{self._base_url}/api/v1/get/{endpoint}"
        headers = {"X-API-Key": self._api_key}
        try:
            async with self._session.get(url, headers=headers) as response:
                if response.status == 403:
                    _LOGGER.error("Authentication failed for endpoint %s", endpoint)
                    raise MailcowAuthenticationError("Invalid API key or permission denied")
                elif response.status >= 500:
                    _LOGGER.error("Server error from Mailcow API: %s", response.status)
                    raise MailcowAPIError(f"Server error {response.status}")
                elif response.status >= 400:
                    _LOGGER.error("Client error from Mailcow API: %s", response.status)
                    raise MailcowAPIError(f"Client error {response.status}")
    
                    try:
                        return await response.json()
                    except Exception as e:
                        _LOGGER.error("Failed to parse JSON response from %s: %s", url, e)
                        raise MailcowAPIError("Invalid JSON response") from e
                        
        except ClientError as err:
            _LOGGER.error("Connection error when calling %s: %s", url, err)
            raise MailcowConnectionError("Failed to connect to Mailcow API") from err
    
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout when connecting to %s", url)
            raise MailcowConnectionError("Connection timed out")
    
        except Exception as ex:
            _LOGGER.exception("Unexpected error while calling Mailcow API: %s", ex)
            raise MailcowAPIError("Unexpected error occurred") from ex

    async def get_mailbox_count(self) -> Optional[int]:
        data = await self._get("mailbox/all")
        return len(data) if isinstance(data, list) else None

    async def get_domain_count(self) -> Optional[int]:
        data = await self._get("domain/all")
        return len(data) if isinstance(data, list) else None

    async def get_status_version(self) -> Optional[str]:
        data = await self._get("status/version")
        return data.get("version") if isinstance(data, dict) else None

    async def get_status_vmail(self) -> Dict[str, Any]:
        result = await self._get("status/vmail")
        return result if isinstance(result, dict) else {}

    async def get_status_containers(self) -> List[Any]:
        result = await self._get("status/containers")
        return result if isinstance(result, list) else []
