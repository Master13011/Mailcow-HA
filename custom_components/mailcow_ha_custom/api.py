"""API client for Mailcow."""
import logging
import requests
import asyncio

_LOGGER = logging.getLogger(__name__)


class MailcowAPI:
    """API client for Mailcow."""

    def __init__(self, base_url, api_key, hass):
        """Initialize the API client."""
        self.base_url = base_url
        self.api_key = api_key
        self.hass = hass  # Store Home Assistant instance

    async def _async_get_data(self, endpoint):
        """Get data from the Mailcow API asynchronously."""
        url = f"{self.base_url}/api/v1/get/{endpoint}"
        headers = {"X-API-Key": self.api_key}
        _LOGGER.debug(f"Calling API endpoint: {url} with headers: {headers}")
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,  # Use the default thread pool
                self._sync_get_request,  # Call the synchronous method
                url,
                headers,
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            # Log the raw response for debugging
            _LOGGER.debug(f"Raw API response: {response.text}")
            return response.json()

        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error calling Mailcow API: {e}")
            raise

    def _sync_get_request(self, url, headers):
        """Perform the synchronous GET request."""
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Sync GET request error: {e}")
            raise


    async def get_mailbox_count(self):
        """Get the number of mailboxes."""
        try:
            data = await self._async_get_data("mailbox/all")
            if data is None:
                _LOGGER.warning("Mailbox data is None")
                return None
            return len(data)
        except Exception as e:
            _LOGGER.error(f"Failed to get mailbox count: {e}")
            return None

    async def get_domain_count(self):
        """Get the number of domains."""
        try:
            data = await self._async_get_data("domain/all")
            if data is None:
                _LOGGER.warning("Domain data is None")
                return None
            return len(data)
        except Exception as e:
            _LOGGER.error(f"Failed to get domain count: {e}")
            return None

    async def get_status_version(self):
        """Get the Mailcow version status."""
        try:
            data = await self._async_get_data("status/version")
            if isinstance(data, dict) and "version" in data:
                return data["version"]
            else:
                _LOGGER.warning(f"Unexpected version data format: {data}")
                return None
        except Exception as e:
            _LOGGER.error(f"Failed to get version status: {e}")
            return None


    async def get_status_vmail(self):
        """Get the vmail status."""
        try:
            data = await self._async_get_data("status/vmail")
            if data is None:
                _LOGGER.warning("Vmail data is None")
                return {}
            return data
        except Exception as e:
            _LOGGER.error(f"Failed to get vmail status: {e}")
            return {}

    async def get_status_containers(self):
        """Get the status of all containers."""
        try:
            data = await self._async_get_data("status/containers")
            if data is None:
                _LOGGER.warning("Containers data is None")
                return []
            return data
        except Exception as e:
            _LOGGER.error(f"Failed to get containers status: {e}")
            return []

    async def close_session(self):
        """Placeholder for session closing (not needed with requests)."""
        pass
