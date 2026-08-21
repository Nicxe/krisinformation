"""Tests for the Krisinformation API client and content models."""

from __future__ import annotations

from datetime import timedelta
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from aioresponses import CallbackResult, aioresponses
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.krisinformation.api import (
    KrisinformationApiClient,
    KrisinformationApiResponseError,
)
from custom_components.krisinformation.const import (
    INTEGRATION_VERSION,
    KRISINFORMATION_NEWS_URL,
    KRISINFORMATION_NOTICES_URL,
    NEWS_UPDATE_INTERVAL_SECONDS,
    NOTICES_UPDATE_INTERVAL_SECONDS,
    USER_AGENT_PRODUCT,
)
from custom_components.krisinformation.coordinator import (
    KrisinformationNewsCoordinator,
    KrisinformationNoticesCoordinator,
)
from custom_components.krisinformation.models import html_to_text

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_news_request_and_normalization(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    news_response: list[dict[str, Any]],
) -> None:
    """Test documented news parameters and safe normalized output."""
    captured: dict[str, Any] = {}

    def capture_request(url, **kwargs):
        captured["url"] = str(url)
        captured["headers"] = kwargs["headers"]
        return CallbackResult(payload=news_response)

    mock_aiohttp.get(
        re.compile(rf"^{re.escape(KRISINFORMATION_NEWS_URL)}.*"),
        callback=capture_request,
    )
    client = KrisinformationApiClient(async_get_clientsession(hass))

    items = await client.async_get_news(language="sv-SE")

    assert [item.identifier for item in items] == ["news-newer", "news-older"]
    newest = items[0]
    assert newest.headline == "Nyare & viktig nyhet"
    assert newest.body_text == "Första stycket. Råd Följ myndighetens råd."
    assert newest.links[0].as_dict() == {
        "text": "Läs mer",
        "url": "https://example.com/news",
    }
    query = parse_qs(urlparse(captured["url"]).query)
    assert query == {
        "allCounties": ["true"],
        "days": ["7"],
        "format": ["json"],
        "includeTest": ["false"],
        "language": ["sv"],
    }
    assert captured["headers"]["Accept"] == "application/json"
    assert USER_AGENT_PRODUCT in captured["headers"]["User-Agent"]
    assert INTEGRATION_VERSION in captured["headers"]["User-Agent"]


async def test_news_count_overrides_days(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
) -> None:
    """Test article count follows the API contract and omits days."""
    captured_url = ""

    def capture_request(url, **kwargs):
        nonlocal captured_url
        captured_url = str(url)
        return CallbackResult(payload=[])

    mock_aiohttp.get(
        re.compile(rf"^{re.escape(KRISINFORMATION_NEWS_URL)}.*"),
        callback=capture_request,
    )
    client = KrisinformationApiClient(async_get_clientsession(hass))

    await client.async_get_news(language="en-US", number_of_articles=12)

    query = parse_qs(urlparse(captured_url).query)
    assert query["language"] == ["en"]
    assert query["numberOfNewsArticles"] == ["12"]
    assert "days" not in query


async def test_notices_request_and_normalization(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    notices_response: list[dict[str, Any]],
) -> None:
    """Test notice metadata is retained and ordered by change time."""
    captured_url = ""

    def capture_request(url, **kwargs):
        nonlocal captured_url
        captured_url = str(url)
        return CallbackResult(payload=notices_response)

    mock_aiohttp.get(
        re.compile(rf"^{re.escape(KRISINFORMATION_NOTICES_URL)}.*"),
        callback=capture_request,
    )
    client = KrisinformationApiClient(async_get_clientsession(hass))

    items = await client.async_get_notices(
        language="sv-SE", county_codes=("14",), all_counties=False
    )

    assert [item.identifier for item in items] == ["notice-newer", "notice-older"]
    newest = items[0]
    assert newest.mobile_body == "Håll dig uppdaterad."
    assert newest.areas[0].description == "Västra Götalands län"
    assert newest.layout.as_dict() == {
        "background_color": "#FFCF00",
        "icon": "notices_announcement",
        "right_aligned_icon": True,
    }
    query = parse_qs(urlparse(captured_url).query)
    assert query == {
        "allCounties": ["false"],
        "counties": ["14"],
        "format": ["json"],
        "language": ["sv"],
    }


async def test_invalid_payload_raises_response_error(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
) -> None:
    """Test malformed API payloads do not leak into entity data."""
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(KRISINFORMATION_NEWS_URL)}.*"),
        payload={"unexpected": True},
    )
    client = KrisinformationApiClient(async_get_clientsession(hass))

    with pytest.raises(KrisinformationApiResponseError):
        await client.async_get_news(language="sv-SE")


async def test_content_coordinators_are_independent(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_aiohttp: aioresponses,
    notices_response: list[dict[str, Any]],
) -> None:
    """Test a news failure does not prevent notices from updating."""
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(KRISINFORMATION_NEWS_URL)}.*"), status=503
    )
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(KRISINFORMATION_NOTICES_URL)}.*"),
        payload=notices_response,
    )
    client = KrisinformationApiClient(async_get_clientsession(hass))
    news = KrisinformationNewsCoordinator(hass, client, mock_config_entry)
    notices = KrisinformationNoticesCoordinator(hass, client, mock_config_entry)

    await news.async_refresh()
    await notices.async_refresh()

    assert news.last_update_success is False
    assert notices.last_update_success is True
    assert notices.data is not None
    assert len(notices.data) == 2
    assert news.update_interval == timedelta(seconds=NEWS_UPDATE_INTERVAL_SECONDS)
    assert notices.update_interval == timedelta(seconds=NOTICES_UPDATE_INTERVAL_SECONDS)


def test_html_to_text_accepts_plain_and_html_content() -> None:
    """Test text extraction is stable for mixed API fields."""
    assert html_to_text("Vanlig text") == "Vanlig text"
    assert html_to_text("<p>Rad ett<br>rad två&nbsp;</p>") == "Rad ett rad två"
