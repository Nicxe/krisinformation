"""Persistent lifecycle tracking for Krisinformation content."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any, Literal

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    EVENT_NEW_NEWS,
    EVENT_NEW_NOTICE,
    EVENT_REMOVED_NEWS,
    EVENT_REMOVED_NOTICE,
    EVENT_UPDATED_NEWS,
    EVENT_UPDATED_NOTICE,
)
from .models import NewsItem, NoticeItem

ContentSource = Literal["news", "notices"]
ContentItem = NewsItem | NoticeItem

_EVENT_TYPES = {
    "news": {
        "new": EVENT_NEW_NEWS,
        "updated": EVENT_UPDATED_NEWS,
        "removed": EVENT_REMOVED_NEWS,
    },
    "notices": {
        "new": EVENT_NEW_NOTICE,
        "updated": EVENT_UPDATED_NOTICE,
        "removed": EVENT_REMOVED_NOTICE,
    },
}


class ContentEventTracker:
    """Diff filtered API snapshots and persist fingerprints across restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._store = Store[dict[str, Any]](
            hass, 1, f"{DOMAIN}.{entry_id}.content_events"
        )
        self._state: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def async_load(self) -> None:
        """Load the last successful snapshots."""
        loaded = await self._store.async_load()
        self._state = loaded if isinstance(loaded, dict) else {}

    @staticmethod
    def _fingerprint(item: ContentItem) -> str:
        payload = json.dumps(
            item.as_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    async def async_process(
        self,
        source: ContentSource,
        items: tuple[ContentItem, ...],
        *,
        scope: str,
    ) -> None:
        """Emit lifecycle events for one successful filtered snapshot."""
        async with self._lock:
            current = {item.identifier: self._fingerprint(item) for item in items}
            previous_source = self._state.get(source)
            if (
                not isinstance(previous_source, dict)
                or previous_source.get("scope") != scope
                or not isinstance(previous_source.get("items"), dict)
            ):
                self._state[source] = {"scope": scope, "items": current}
                await self._store.async_save(self._state)
                return

            previous: dict[str, str] = previous_source["items"]
            if current == previous:
                return

            current_items = {item.identifier: item for item in items}
            for identifier in sorted(current.keys() - previous.keys()):
                item = current_items[identifier]
                self._hass.bus.async_fire(
                    _EVENT_TYPES[source]["new"],
                    {"source": source, **item.as_dict()},
                )
            for identifier in sorted(current.keys() & previous.keys()):
                if current[identifier] == previous[identifier]:
                    continue
                item = current_items[identifier]
                self._hass.bus.async_fire(
                    _EVENT_TYPES[source]["updated"],
                    {"source": source, **item.as_dict()},
                )
            for identifier in sorted(previous.keys() - current.keys()):
                self._hass.bus.async_fire(
                    _EVENT_TYPES[source]["removed"],
                    {"source": source, "identifier": identifier},
                )

            self._state[source] = {"scope": scope, "items": current}
            await self._store.async_save(self._state)
