import pytest
from custom_components.mailcow.api import MailcowAPI

class FakeHass:
    def __init__(self):
        self.loop = None

@pytest.mark.asyncio
async def test_get_mailbox_count_success(monkeypatch):
    async def fake_get_data(self, endpoint):
        assert endpoint == "mailbox/all"
        return [{}] * 3

    monkeypatch.setattr(MailcowAPI, "_async_get_data", fake_get_data)

    api = MailcowAPI("http://fake", "key", FakeHass())
    count = await api.get_mailbox_count()
    assert count == 3
