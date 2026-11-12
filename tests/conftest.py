"""Fixtures for the Mailcow tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .common import PATCH_API, PATCH_LATEST, make_api


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def mailcow_api() -> Generator[MagicMock]:
    """Replace the Mailcow API client and the GitHub lookup for a full setup.

    The fake client answers like a healthy server. Tests can change what it
    returns (``mailcow_api.get_status_version.return_value = ...``) or make it
    fail (``...side_effect = ...``) before the integration is set up.
    ``mailcow_api.latest_mock`` is the GitHub lookup (latest version "2025-04").
    """
    api = make_api()
    latest = AsyncMock(return_value="2025-04")
    api.latest_mock = latest
    with patch(PATCH_API, return_value=api), patch(PATCH_LATEST, new=latest):
        yield api
