"""Fixtures for Krisinformation tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generator

import pytest
from aioresponses import aioresponses

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.krisinformation.const import (
    DOMAIN,
    CONF_NAME,
    CONF_MUNICIPALITY,
    CONF_LANGUAGE,
    CONF_INCLUDE_UPDATE_CANCEL,
    CONF_SEVERITY_MIN,
    CONF_API_ENV,
    CONF_INCLUDE_NATIONAL,
    CONF_INCLUDE_NEWS,
    CONF_INCLUDE_NOTICES,
    CONF_INCLUDE_UNLOCATED,
    CONF_MAX_ITEMS,
    CONF_NEWS_DAYS,
    API_ENV_PRODUCTION,
    LANGUAGE_DEFAULT,
    INCLUDE_UPDATE_CANCEL_DEFAULT,
    SEVERITY_MIN_DEFAULT,
    PRODUCTION_BASE_URL,
    TEST_BASE_URL,
)

_CONTENT_OPTIONS = {
    # VMA tests opt in to content explicitly so their network mocks remain isolated.
    CONF_INCLUDE_NEWS: False,
    CONF_INCLUDE_NOTICES: False,
    CONF_NEWS_DAYS: 7,
    CONF_MAX_ITEMS: 10,
    CONF_INCLUDE_NATIONAL: True,
    CONF_INCLUDE_UNLOCATED: True,
}


def load_fixture(filename: str) -> Any:
    """Load a JSON fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations) -> None:
    """Enable custom integrations for this test module."""
    return None


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for Stockholm."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Krisinformation (Stockholm)",
        data={
            CONF_NAME: "Krisinformation",
            CONF_MUNICIPALITY: "Stockholm",
        },
        options={
            **_CONTENT_OPTIONS,
            CONF_LANGUAGE: LANGUAGE_DEFAULT,
            CONF_INCLUDE_UPDATE_CANCEL: INCLUDE_UPDATE_CANCEL_DEFAULT,
            CONF_SEVERITY_MIN: SEVERITY_MIN_DEFAULT,
            CONF_API_ENV: API_ENV_PRODUCTION,
        },
        entry_id="test_entry_id",
        version=4,
    )


@pytest.fixture
def mock_config_entry_hela_sverige() -> MockConfigEntry:
    """Create a mock config entry for all of Sweden (no geocode filter)."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Krisinformation (Hela Sverige)",
        data={
            CONF_NAME: "Krisinformation",
            CONF_MUNICIPALITY: "Hela Sverige",
        },
        options={
            **_CONTENT_OPTIONS,
            CONF_LANGUAGE: LANGUAGE_DEFAULT,
            CONF_INCLUDE_UPDATE_CANCEL: INCLUDE_UPDATE_CANCEL_DEFAULT,
            CONF_SEVERITY_MIN: SEVERITY_MIN_DEFAULT,
            CONF_API_ENV: API_ENV_PRODUCTION,
        },
        entry_id="test_entry_hela_sverige",
        version=4,
    )


@pytest.fixture
def mock_config_entry_include_updates() -> MockConfigEntry:
    """Create a mock config entry that includes Update/Cancel messages."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Krisinformation (Stockholm)",
        data={
            CONF_NAME: "Krisinformation",
            CONF_MUNICIPALITY: "Stockholm",
        },
        options={
            **_CONTENT_OPTIONS,
            CONF_LANGUAGE: LANGUAGE_DEFAULT,
            CONF_INCLUDE_UPDATE_CANCEL: True,
            CONF_SEVERITY_MIN: SEVERITY_MIN_DEFAULT,
            CONF_API_ENV: API_ENV_PRODUCTION,
        },
        entry_id="test_entry_with_updates",
        version=4,
    )


@pytest.fixture
def mock_config_entry_severity_severe() -> MockConfigEntry:
    """Create a mock config entry with Severe minimum severity."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Krisinformation (Stockholm)",
        data={
            CONF_NAME: "Krisinformation",
            CONF_MUNICIPALITY: "Stockholm",
        },
        options={
            **_CONTENT_OPTIONS,
            CONF_LANGUAGE: LANGUAGE_DEFAULT,
            CONF_INCLUDE_UPDATE_CANCEL: INCLUDE_UPDATE_CANCEL_DEFAULT,
            CONF_SEVERITY_MIN: "Severe",
            CONF_API_ENV: API_ENV_PRODUCTION,
        },
        entry_id="test_entry_severity_severe",
        version=4,
    )


@pytest.fixture
def empty_response() -> dict[str, Any]:
    """Empty VMA API response fixture."""
    return load_fixture("vma_empty.json")


@pytest.fixture
def single_alert_response() -> dict[str, Any]:
    """Single alert VMA API response fixture."""
    return load_fixture("vma_single_alert.json")


@pytest.fixture
def multiple_alerts_response() -> dict[str, Any]:
    """Multiple alerts VMA API response fixture."""
    return load_fixture("vma_multiple_alerts.json")


@pytest.fixture
def update_cancel_response() -> dict[str, Any]:
    """Update and Cancel message types fixture."""
    return load_fixture("vma_update_cancel.json")


@pytest.fixture
def news_response() -> list[dict[str, Any]]:
    """Krisinformation news API response fixture."""
    return load_fixture("krisinformation_news.json")


@pytest.fixture
def notices_response() -> list[dict[str, Any]]:
    """Krisinformation notices API response fixture."""
    return load_fixture("krisinformation_notices.json")


@pytest.fixture
def mock_aiohttp() -> Generator[aioresponses, None, None]:
    """Mock aiohttp requests using aioresponses."""
    with aioresponses() as m:
        yield m


@pytest.fixture
def production_url() -> str:
    """Return the production API URL."""
    return PRODUCTION_BASE_URL


@pytest.fixture
def test_url() -> str:
    """Return the test API URL."""
    return TEST_BASE_URL
