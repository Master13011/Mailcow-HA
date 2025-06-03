import pytest


@pytest.mark.asyncio
async def test_coordinator_update_data(coordinator, mock_api):
    await coordinator.async_refresh()

    data = coordinator.data
    assert data is not None
    assert data["version"] == "v2.0"
    assert data["mailbox_count"] == 5
    assert data["domain_count"] == 2
    assert isinstance(data["vmail_status"], dict)
    assert isinstance(data["containers_status"], list)
    assert len(data["containers_status"]) == 2
