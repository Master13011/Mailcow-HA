import pytest
from unittest.mock import AsyncMock

import homeassistant.core as ha_core

from custom_components.mailcow.api import MailcowAPI
from custom_components.mailcow.coordinator import MailcowCoordinator


@pytest.fixture
def mock_api():
    api = AsyncMock(spec=MailcowAPI)
    api.get_status_version.return_value = "v2.0"
    api.get_mailbox_count.return_value = 5
    api.get_domain_count.return_value = 2
    api.get_status_vmail.return_value = {"used_percent": "50%","type":"ssd","disk":"/dev/sda","used":"5GB","total":"10GB"}
    api.get_status_containers.return_value = [
        {"id": "container1", "name": "mailcow_mail", "state": "running"},
        {"id": "container2", "name": "mailcow_db", "state": "stopped"},
    ]
    return api


@pytest.fixture
async def coordinator(hass, mock_api):
    coordinator = MailcowCoordinator(
        hass=hass,
        api=mock_api,
        scan_interval=10,
        disable_check_at_night=False,
        entry_id="test_entry",
        base_url="https://mailcow.example.com",
        session=None
    )
    await coordinator.async_refresh()
    return coordinator
