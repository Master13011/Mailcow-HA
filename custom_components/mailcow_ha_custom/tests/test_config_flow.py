import pytest
from unittest.mock import patch, AsyncMock

from homeassistant import data_entry_flow
from custom_components.mailcow.config_flow import MailcowConfigFlow, CannotConnect, AuthenticationError
from custom_components.mailcow.const import DOMAIN

@pytest.mark.asyncio
async def test_user_flow_success(hass):
    """Test a successful user config flow."""

    flow = MailcowConfigFlow()
    flow.hass = hass

    user_input = {
        "base_url": "https://mailcow.example.com",
        "api_key": "fakeapikey123",
        "disable_check_at_night": True,
        "scan_interval": 15,
    }

    with patch(
        "custom_components.mailcow.config_flow.MailcowAPI.get_status_version",
        new=AsyncMock(return_value="v2.0")
    ):
        result = await flow.async_step_user(user_input)
        assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
        assert result["title"] == "Mailcow"
        assert result["data"]["base_url"] == user_input["base_url"]
        assert result["data"]["api_key"] == user_input["api_key"]
        assert result["options"]["disable_check_at_night"] == True
        assert result["options"]["scan_interval"] == 15


@pytest.mark.asyncio
async def test_user_flow_cannot_connect(hass):
    flow = MailcowConfigFlow()
    flow.hass = hass

    user_input = {
        "base_url": "https://badurl.example.com",
        "api_key": "invalidkey",
    }

    with patch(
        "custom_components.mailcow.config_flow.MailcowAPI.get_status_version",
        new=AsyncMock(return_value=None)
    ):
        result = await flow.async_step_user(user_input)
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert "cannot_connect" in result["errors"].values()


@pytest.mark.asyncio
async def test_user_flow_authentication_error(hass):
    flow = MailcowConfigFlow()
    flow.hass = hass

    user_input = {
        "base_url": "https://mailcow.example.com",
        "api_key": "wrongkey",
    }

    # Simuler une erreur 403 pour forcer AuthenticationError
    mock_exc = Exception()
    setattr(mock_exc, "response", type("resp", (), {"status_code": 403})())

    with patch(
        "custom_components.mailcow.config_flow.MailcowAPI.get_status_version",
        new=AsyncMock(side_effect=mock_exc)
    ):
        result = await flow.async_step_user(user_input)
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert "invalid_auth" in result["errors"].values()
