"""Tests for Krisinformation news and notice sensors."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.krisinformation.const import (
    DOMAIN,
    EVENT_NEW_NEWS,
    KRISINFORMATION_NEWS_URL,
    KRISINFORMATION_NOTICES_URL,
    PRODUCTION_BASE_URL,
)
from custom_components.krisinformation.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.krisinformation.helpers import (
    content_device_identifier,
    news_unique_id,
    notices_unique_id,
)
from custom_components.krisinformation.sensor import (
    KrisinformationNewsSensor,
    KrisinformationNoticesSensor,
)

from pytest_homeassistant_custom_component.common import MockConfigEntry


def _content_entry(entry_id: str = "content_entry") -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Krisinformation (Hela Sverige)",
        data={"name": "Krisinformation", "municipality": "Hela Sverige"},
        options={
            "language": "sv-SE",
            "include_update_cancel": False,
            "severity_min": "Minor",
            "api_environment": "production",
            "include_news": True,
            "include_notices": True,
            "news_days": 7,
            "max_items": 10,
            "include_national": True,
            "include_unlocated": True,
        },
        entry_id=entry_id,
        version=4,
    )


def _mock_sources(
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
    news_response: list[dict[str, Any]],
    notices_response: list[dict[str, Any]],
    *,
    news_status: int = 200,
) -> None:
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"), payload=empty_response
    )
    if news_status == 200:
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(KRISINFORMATION_NEWS_URL)}.*"),
            payload=news_response,
        )
    else:
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(KRISINFORMATION_NEWS_URL)}.*"),
            status=news_status,
        )
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(KRISINFORMATION_NOTICES_URL)}.*"),
        payload=notices_response,
    )


async def test_content_sensors_expose_bounded_normalized_items(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
    news_response: list[dict[str, Any]],
    notices_response: list[dict[str, Any]],
) -> None:
    """Test content sensors, stable IDs, device grouping, and attributes."""
    entry = _content_entry()
    _mock_sources(
        mock_aiohttp,
        empty_response,
        news_response,
        notices_response,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    news_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, news_unique_id(entry.entry_id)
    )
    notices_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, notices_unique_id(entry.entry_id)
    )
    assert news_entity_id is not None
    assert notices_entity_id is not None

    news_state = hass.states.get(news_entity_id)
    notices_state = hass.states.get(notices_entity_id)
    assert news_state is not None
    assert notices_state is not None
    assert news_state.state == "2"
    assert notices_state.state == "2"
    assert len(news_state.attributes["items"]) == 2
    assert news_state.attributes["latest"]["identifier"] == "news-newer"
    assert notices_state.attributes["latest"]["identifier"] == "notice-newer"
    assert "<" not in news_state.attributes["latest"]["body_text"]

    device_registry = dr.async_get(hass)
    content_device = device_registry.async_get_device(
        identifiers={content_device_identifier(entry.entry_id)}
    )
    assert content_device is not None
    assert content_device.manufacturer == "Myndigheten för civilt försvar"
    assert KrisinformationNewsSensor._unrecorded_attributes == frozenset(
        {"items", "latest"}
    )
    assert KrisinformationNoticesSensor._unrecorded_attributes == frozenset(
        {"items", "latest"}
    )

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert set(diagnostics["sources"]) == {"vma", "news", "notices"}
    assert diagnostics["sources"]["news"]["last_success"] is True
    assert len(diagnostics["sources"]["news"]["data"]) == 2
    assert diagnostics["sources"]["notices"]["update_interval"] == 300


async def test_content_source_failure_does_not_block_vma_or_notices(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
    news_response: list[dict[str, Any]],
    notices_response: list[dict[str, Any]],
) -> None:
    """Test independent source availability in the running integration."""
    entry = _content_entry("partial_failure")
    _mock_sources(
        mock_aiohttp,
        empty_response,
        news_response,
        notices_response,
        news_status=503,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    news_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, news_unique_id(entry.entry_id)
    )
    notices_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, notices_unique_id(entry.entry_id)
    )
    vma_entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{DOMAIN}_{entry.entry_id}_vma_count"
    )
    assert news_entity_id is not None
    assert notices_entity_id is not None
    assert vma_entity_id is not None
    news_state = hass.states.get(news_entity_id)
    notices_state = hass.states.get(notices_entity_id)
    vma_state = hass.states.get(vma_entity_id)
    assert news_state is not None
    assert notices_state is not None
    assert vma_state is not None
    assert news_state.state == "unavailable"
    assert notices_state.state == "2"
    assert vma_state.state == "0"


async def test_news_refresh_emits_normalized_new_item_event(
    hass: HomeAssistant,
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
    news_response: list[dict[str, Any]],
    notices_response: list[dict[str, Any]],
) -> None:
    """Test coordinator refreshes expose new content to automations."""
    entry = _content_entry("news_event")
    _mock_sources(
        mock_aiohttp,
        empty_response,
        news_response,
        notices_response,
    )
    events = []
    hass.bus.async_listen(EVENT_NEW_NEWS, events.append)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert events == []

    changed_response = deepcopy(news_response)
    added = deepcopy(news_response[1])
    added["Identifier"] = "news-added"
    added["ContentId"] = 102
    added["Updated"] = "2026-08-21T13:00:00+02:00"
    changed_response.append(added)
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(KRISINFORMATION_NEWS_URL)}.*"),
        payload=changed_response,
    )

    await entry.runtime_data.news_coordinator.async_refresh()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["source"] == "news"
    assert events[0].data["identifier"] == "news-added"
    assert events[0].data["headline"] == "Nyare & viktig nyhet"


async def test_disabled_content_sources_do_not_create_entities(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_aiohttp: aioresponses,
    empty_response: dict[str, Any],
) -> None:
    """Test VMA-only configurations avoid content entities and API polling."""
    mock_aiohttp.get(
        re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"), payload=empty_response
    )
    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry = er.async_get(hass)
    assert (
        entity_registry.async_get_entity_id(
            "sensor", DOMAIN, news_unique_id(mock_config_entry.entry_id)
        )
        is None
    )
    assert (
        entity_registry.async_get_entity_id(
            "sensor", DOMAIN, notices_unique_id(mock_config_entry.entry_id)
        )
        is None
    )
