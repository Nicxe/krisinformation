"""Regressions for Krisinformation's camelCase API responses (issue #99).

The news snapshot was fetched from the public v3/news endpoint on 2026-11-17.
CamelCase notice responses below are synthetic variants of the legacy fixtures.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from aioresponses import aioresponses
import pytest
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.krisinformation.api import (
    KrisinformationApiClient,
    KrisinformationApiResponseError,
)
from custom_components.krisinformation.const import (
    DOMAIN,
    EVENT_REMOVED_NEWS,
    EVENT_REMOVED_NOTICE,
    KRISINFORMATION_NEWS_URL,
    KRISINFORMATION_NOTICES_URL,
    PRODUCTION_BASE_URL,
)
from custom_components.krisinformation.helpers import news_unique_id, notices_unique_id
from custom_components.krisinformation.models import NewsItem, NoticeLayout

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import load_fixture

_SOURCE_URLS = {
    "news": KRISINFORMATION_NEWS_URL,
    "notices": KRISINFORMATION_NOTICES_URL,
}


def _camelcase(value: Any) -> Any:
    """Build synthetic camelCase variants, including nested API objects."""
    if isinstance(value, dict):
        return {
            key[0].lower() + key[1:]: _camelcase(item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_camelcase(item) for item in value]
    return value


def _entry(location: str = "Hela Sverige", **options: Any) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Krisinformation ({location})",
        data={"name": "Krisinformation", "municipality": location},
        options={
            "language": "sv-SE",
            "api_environment": "production",
            "include_news": True,
            "include_notices": True,
            "include_smhi_weather_warnings": True,
            "news_days": 7,
            "max_items": 10,
            "include_national": True,
            "include_unlocated": True,
            **options,
        },
        version=5,
    )


def _mock_sources(
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
    news: list[dict[str, Any]],
    notices: list[dict[str, Any]],
) -> None:
    for url, payload in (
        (PRODUCTION_BASE_URL, empty_response),
        (KRISINFORMATION_NEWS_URL, news),
        (KRISINFORMATION_NOTICES_URL, notices),
    ):
        mock_aiohttp.get(re.compile(rf"^{re.escape(url)}(?:\?|$)"), payload=payload)


def _state(hass: HomeAssistant, entry: MockConfigEntry, source: str) -> State:
    unique_id = news_unique_id if source == "news" else notices_unique_id
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, unique_id(entry.entry_id)
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    return state


async def test_real_camelcase_news_reaches_sensor(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
) -> None:
    """Keep the real SE-Alert article, its national area, links, and timestamps."""
    response = load_fixture("krisinformation_news_camelcase.json")
    entry = _entry(include_unlocated=False)
    _mock_sources(mock_aiohttp, empty_response, response, [])
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = _state(hass, entry, "news")
    assert state.state == "1"
    item = state.attributes["latest"]
    assert state.attributes["items"] == [item]
    assert item["identifier"] == "1277"
    assert item["content_id"] == 1277
    assert item["headline"] == "Test av nytt varningssystem 7 december"
    assert item["body_text"].startswith("Vid testet ger telefonen ifrån sig")
    assert item["updated"] == "2026-11-17T10:37:43+01:00"
    assert item["published"] == "2026-11-17T09:41:26+01:00"
    assert item["areas"] == [{"type": "Country", "description": "Sverige"}]
    assert item["links"] == response[0]["links"]
    assert item["web_url"] == response[0]["web"]
    assert item["push"] is False
    assert item["is_test"] is False


@pytest.mark.parametrize("camelcase", [False, True], ids=["legacy", "camelcase"])
async def test_content_formats_preserve_county_and_smhi_filters(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
    news_response: list[dict[str, Any]],
    notices_response: list[dict[str, Any]],
    camelcase: bool,
) -> None:
    """Retain local content and nested metadata while filtering SMHI notices."""
    news = deepcopy(news_response)
    notices = deepcopy(notices_response)
    news[1]["Area"] = deepcopy(notices[1]["Area"])
    notices[0]["Area"] = deepcopy(notices[1]["Area"])
    notices[0]["Layout"]["Icon"] = "warning_SMHI_class_2"
    other_county_notice = deepcopy(notices[1])
    other_county_notice["Id"] = "notice-other-county"
    other_county_notice["Area"] = deepcopy(news[0]["Area"])
    notices.append(other_county_notice)
    if camelcase:
        news, notices = _camelcase(news), _camelcase(notices)
    entry = _entry(
        "Göteborg",
        include_national=False,
        include_unlocated=False,
        include_smhi_weather_warnings=False,
    )
    _mock_sources(mock_aiohttp, empty_response, news, notices)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    news_state = _state(hass, entry, "news")
    notices_state = _state(hass, entry, "notices")
    assert news_state.state == notices_state.state == "1"
    news_item = news_state.attributes["latest"]
    notice_item = notices_state.attributes["latest"]
    assert news_item["identifier"] == "news-newer"
    assert news_item["headline"] == "Nyare & viktig nyhet"
    assert news_item["links"] == [
        {"text": "Läs mer", "url": "https://example.com/news"}
    ]
    assert notice_item["identifier"] == "notice-newer"
    assert notice_item["areas"] == [
        {"type": "County", "description": "Västra Götalands län"}
    ]
    assert notice_item["mobile_body"] == "Håll dig uppdaterad."
    assert notice_item["changed"] == "2026-08-21T14:00:00+02:00"
    assert notice_item["layout"] == {
        "background_color": "#FFCF00",
        "icon": "notices_announcement",
        "right_aligned_icon": True,
    }
    assert notice_item["links"] == [
        {"text": "Ansvarig myndighet", "url": "https://example.com/notice"}
    ]
    assert notice_item["is_smhi_weather_warning"] is False
    assert notice_item["sort_order"] == 0


@pytest.mark.parametrize("source", ["news", "notices"])
async def test_empty_content_response_is_valid(
    hass: HomeAssistant, mock_aiohttp: aioresponses, source: str
) -> None:
    """An empty upstream list remains a successful empty collection."""
    mock_aiohttp.get(re.compile(rf"^{re.escape(_SOURCE_URLS[source])}.*"), payload=[])
    client = KrisinformationApiClient(async_get_clientsession(hass))

    assert await getattr(client, f"async_get_{source}")(language="sv-SE") == ()


@pytest.mark.parametrize("source", ["news", "notices"])
@pytest.mark.parametrize(
    "include_valid_item", [False, True], ids=["invalid", "partial"]
)
async def test_missing_identity_is_an_api_error(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    source: str,
    include_valid_item: bool,
) -> None:
    """Never silently discard unknown content as if no information existed."""
    payload = [{"headline": "Missing identity"}]
    if include_valid_item:
        payload.insert(0, {"contentId": 1, "headline": "Valid article"})
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(_SOURCE_URLS[source])}.*"), payload=payload
    )
    client = KrisinformationApiClient(async_get_clientsession(hass))

    with pytest.raises(KrisinformationApiResponseError):
        await getattr(client, f"async_get_{source}")(language="sv-SE")


@pytest.mark.parametrize("source", ["news", "notices"])
async def test_invalid_content_is_unavailable_instead_of_zero(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
    source: str,
) -> None:
    """Expose an invalid source as unavailable while the other source stays valid."""
    entry = _entry()
    payloads = {"news": [], "notices": []}
    payloads[source] = [{"headline": "Missing identity"}]
    _mock_sources(mock_aiohttp, empty_response, **payloads)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert _state(hass, entry, source).state == "unavailable"
    other_source = "notices" if source == "news" else "news"
    assert _state(hass, entry, other_source).state == "0"


@pytest.mark.parametrize("source", ["news", "notices"])
async def test_invalid_refresh_preserves_items_without_removal_events(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
    news_response: list[dict[str, Any]],
    notices_response: list[dict[str, Any]],
    source: str,
) -> None:
    """A malformed refresh keeps the last snapshot and never invents removals."""
    entry = _entry()
    _mock_sources(mock_aiohttp, empty_response, news_response, notices_response)
    removed_events = []
    event_type = EVENT_REMOVED_NEWS if source == "news" else EVENT_REMOVED_NOTICE
    hass.bus.async_listen(event_type, removed_events.append)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    original_items = _state(hass, entry, source).attributes["items"]
    assert len(original_items) == 2
    coordinator = getattr(entry.runtime_data, f"{source}_coordinator")
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(_SOURCE_URLS[source])}.*"),
        payload=[{"headline": "Missing identity"}],
    )

    await coordinator.async_request_refresh()
    await hass.async_block_till_done()

    state = _state(hass, entry, source)
    assert state.state == "unavailable"
    assert [item.as_dict() for item in coordinator.data] == original_items
    assert removed_events == []

    mock_aiohttp.get(
        re.compile(rf"^{re.escape(_SOURCE_URLS[source])}.*"),
        payload=news_response if source == "news" else notices_response,
    )
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    restored_state = _state(hass, entry, source)
    assert restored_state.state == "2"
    assert restored_state.attributes["items"] == original_items
    assert removed_events == []


@pytest.mark.parametrize("source", ["news", "notices"])
@pytest.mark.parametrize("camelcase", [False, True], ids=["legacy", "camelcase"])
async def test_content_id_zero_is_a_valid_identity_fallback(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    source: str,
    camelcase: bool,
) -> None:
    """Keep ContentId fallback in both formats without dropping a falsey value."""
    payload = [{"ContentId": 0, "Headline": "Content ID only"}]
    if camelcase:
        payload = _camelcase(payload)
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(_SOURCE_URLS[source])}.*"), payload=payload
    )
    client = KrisinformationApiClient(async_get_clientsession(hass))

    items = await getattr(client, f"async_get_{source}")(language="sv-SE")

    assert len(items) == 1
    assert items[0].identifier == "0"
    assert items[0].headline == "Content ID only"


def test_camelcase_falsey_values_do_not_fall_back_to_legacy_fields() -> None:
    """Prefer present camelCase keys even when their values are falsey."""
    item = NewsItem.from_api(
        {
            "identifier": None,
            "Identifier": "legacy-id",
            "contentId": 0,
            "ContentId": 7,
            "headline": "",
            "Headline": "Legacy headline",
            "push": False,
            "Push": True,
        }
    )
    assert item.identifier == "0"
    assert item.headline == ""
    assert item.push is False
    layout = NoticeLayout.from_api(
        {"rightAlignedIcon": False, "RightAlignedIcon": True}
    )
    assert layout.right_aligned_icon is False
