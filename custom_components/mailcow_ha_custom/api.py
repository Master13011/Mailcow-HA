import logging
from aiohttp import ClientSession, ClientError
from .const import CONF_API_KEY, CONF_BASE_URL

_LOGGER = logging.getLogger(__name__)

class MailcowAPI:
    """Asynchronous Mailcow API client."""

    def __init__(self, config_data: dict, session: ClientSession) -> None:
        self._base_url = config_data[CONF_BASE_URL].rstrip("/")
        self._api_key = config_data[CONF_API_KEY]
        self._session = session

    async def _get(self, endpoint: str) -> dict | list | None:
        """Generic GET request to Mailcow API."""
        url = f"{self._base_url}/api/v1/get/{endpoint}"
        headers = {"X-API-Key": self._api_key}
        try:
            async with self._session.get(url, headers=headers, timeout=10) as response:
                response.raise_for_status()
                return await response.json()
        except ClientError as err:
            _LOGGER.error("Mailcow API request failed: %s", err)
        except Exception as ex:
            _LOGGER.exception("Unexpected error while calling Mailcow API: %s", ex)
        return None

    async def get_mailbox_count(self) -> int | None:
        data = await self._get("mailbox/all")
        return len(data) if isinstance(data, list) else None

    async def get_domain_count(self) -> int | None:
        data = await self._get("domain/all")
        return len(data) if isinstance(data, list) else None

    async def get_status_version(self) -> str | None:
        data = await self._get("status/version")
        return data.get("version") if isinstance(data, dict) else None

    async def get_status_vmail(self) -> dict:
        return await self._get("status/vmail") or {}

    async def get_status_containers(self) -> list:
        return await self._get("status/containers") or []
