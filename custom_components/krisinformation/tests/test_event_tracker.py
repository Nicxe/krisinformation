"""Tests for persistent Krisinformation content lifecycle events."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from homeassistant.core import Event, HomeAssistant

from custom_components.krisinformation.const import (
    EVENT_NEW_NEWS,
    EVENT_NEW_NOTICE,
    EVENT_REMOVED_NEWS,
    EVENT_UPDATED_NEWS,
)
from custom_components.krisinformation.event_tracker import ContentEventTracker
from custom_components.krisinformation.models import NewsItem, NoticeItem


async def test_news_events_are_suppressed_on_seed_and_persisted(
    hass: HomeAssistant,
    news_response: list[dict[str, Any]],
) -> None:
    """Test first-load suppression, lifecycle events, and restart persistence."""
    events: list[Event] = []
    for event_type in (EVENT_NEW_NEWS, EVENT_UPDATED_NEWS, EVENT_REMOVED_NEWS):
        hass.bus.async_listen(event_type, events.append)

    original = tuple(NewsItem.from_api(item) for item in news_response)
    tracker = ContentEventTracker(hass, "event_entry")
    await tracker.async_load()
    await tracker.async_process("news", original, scope="scope-a")
    await hass.async_block_till_done()
    assert events == []

    updated = replace(original[0], headline="Ändrad rubrik")
    added = replace(original[0], identifier="news-added")
    await tracker.async_process("news", (updated, added), scope="scope-a")
    await hass.async_block_till_done()

    assert {event.event_type for event in events} == {
        EVENT_NEW_NEWS,
        EVENT_UPDATED_NEWS,
        EVENT_REMOVED_NEWS,
    }
    assert (
        next(event for event in events if event.event_type == EVENT_NEW_NEWS).data[
            "identifier"
        ]
        == "news-added"
    )
    assert (
        next(event for event in events if event.event_type == EVENT_UPDATED_NEWS).data[
            "headline"
        ]
        == "Ändrad rubrik"
    )
    assert next(
        event for event in events if event.event_type == EVENT_REMOVED_NEWS
    ).data == {"source": "news", "identifier": "news-newer"}

    events.clear()
    restarted = ContentEventTracker(hass, "event_entry")
    await restarted.async_load()
    await restarted.async_process("news", (updated, added), scope="scope-a")
    await hass.async_block_till_done()
    assert events == []


async def test_filter_scope_change_reseeds_without_events(
    hass: HomeAssistant,
    news_response: list[dict[str, Any]],
) -> None:
    """Test geographic or language changes do not create misleading events."""
    events: list[Event] = []
    hass.bus.async_listen(EVENT_NEW_NEWS, events.append)
    items = tuple(NewsItem.from_api(item) for item in news_response)
    tracker = ContentEventTracker(hass, "scope_entry")
    await tracker.async_load()

    await tracker.async_process("news", items[:1], scope="scope-a")
    await tracker.async_process("news", items, scope="scope-b")
    await hass.async_block_till_done()

    assert events == []


async def test_notices_use_notice_event_types(
    hass: HomeAssistant,
    notices_response: list[dict[str, Any]],
) -> None:
    """Test notice lifecycle events remain distinct from news events."""
    events: list[Event] = []
    hass.bus.async_listen(EVENT_NEW_NOTICE, events.append)
    items = tuple(NoticeItem.from_api(item) for item in notices_response)
    tracker = ContentEventTracker(hass, "notice_entry")
    await tracker.async_load()

    await tracker.async_process("notices", items[:1], scope="scope")
    await tracker.async_process("notices", items, scope="scope")
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["source"] == "notices"
    assert events[0].data["identifier"] == "notice-newer"
