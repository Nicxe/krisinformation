from __future__ import annotations

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.const import CONF_ID, CONF_TYPE

from custom_components.krisinformation import frontend
from custom_components.krisinformation.const import (
    CARD_CANONICAL_BASE_URL,
    CARD_LEGACY_BASE_URL,
)


class _FakeResources:
    def __init__(self, items: list[dict] | None = None) -> None:
        self._items = list(items or [])
        self.loaded = False
        self.create_calls = 0
        self.update_calls = 0

    async def async_load(self) -> None:
        self.loaded = True

    def async_items(self) -> list[dict]:
        return list(self._items)

    async def async_create_item(self, data: dict) -> dict:
        self.create_calls += 1
        item = {
            CONF_ID: f"generated-{self.create_calls}",
            "url": data["url"],
            CONF_TYPE: data.get("res_type", "module"),
        }
        self._items.append(item)
        return item

    async def async_update_item(self, item_id: str, updates: dict) -> dict:
        self.update_calls += 1
        for item in self._items:
            if item[CONF_ID] == item_id:
                item["url"] = updates["url"]
                if "res_type" in updates:
                    item[CONF_TYPE] = updates["res_type"]
                return item
        raise KeyError(item_id)

@pytest.mark.asyncio
async def test_ensure_resource_creates_when_missing(hass, monkeypatch) -> None:
    from types import SimpleNamespace

    resources = _FakeResources()
    hass.data[LOVELACE_DATA] = SimpleNamespace(resources=resources)

    async def _fake_cache_key(_hass):
        return "2.2.0-123"

    monkeypatch.setattr(frontend, "_cache_key_for_dev", _fake_cache_key)

    ok = await frontend._async_ensure_card_resource(hass)

    assert ok is True
    assert resources.create_calls == 1
    created = resources.async_items()[0]
    assert created[CONF_TYPE] == "module"
    assert created["url"] == f"{CARD_LEGACY_BASE_URL}?v=2.2.0-123"


@pytest.mark.asyncio
async def test_ensure_resource_updates_existing_canonical(hass, monkeypatch) -> None:
    from types import SimpleNamespace

    resources = _FakeResources(
        [
            {
                CONF_ID: "abc",
                CONF_TYPE: "module",
                "url": f"{CARD_CANONICAL_BASE_URL}?v=old",
            }
        ]
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(resources=resources)

    async def _fake_cache_key(_hass):
        return "2.2.0-456"

    monkeypatch.setattr(frontend, "_cache_key_for_dev", _fake_cache_key)

    ok = await frontend._async_ensure_card_resource(hass)

    assert ok is True
    assert resources.update_calls == 1
    assert resources.async_items()[0]["url"] == f"{CARD_LEGACY_BASE_URL}?v=2.2.0-456"


@pytest.mark.asyncio
async def test_ensure_resource_prefers_existing_local_over_canonical(
    hass, monkeypatch
) -> None:
    from types import SimpleNamespace

    resources = _FakeResources(
        [
            {CONF_ID: "local", CONF_TYPE: "module", "url": CARD_LEGACY_BASE_URL},
            {CONF_ID: "canonical", CONF_TYPE: "module", "url": CARD_CANONICAL_BASE_URL},
        ]
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(resources=resources)

    async def _fake_cache_key(_hass):
        return "2.2.0-789"

    monkeypatch.setattr(frontend, "_cache_key_for_dev", _fake_cache_key)

    ok = await frontend._async_ensure_card_resource(hass)

    assert ok is True
    assert resources.update_calls == 1
    items = {item[CONF_ID]: item for item in resources.async_items()}
    assert items["local"]["url"] == f"{CARD_LEGACY_BASE_URL}?v=2.2.0-789"
    assert items["canonical"]["url"] == CARD_CANONICAL_BASE_URL


@pytest.mark.asyncio
async def test_ensure_resource_is_idempotent(hass, monkeypatch) -> None:
    from types import SimpleNamespace

    resources = _FakeResources(
        [
            {
                CONF_ID: "abc",
                CONF_TYPE: "module",
                "url": f"{CARD_LEGACY_BASE_URL}?v=stable",
            }
        ]
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(resources=resources)

    async def _fake_cache_key(_hass):
        return "stable"

    monkeypatch.setattr(frontend, "_cache_key_for_dev", _fake_cache_key)

    ok = await frontend._async_ensure_card_resource(hass)

    assert ok is True
    assert resources.create_calls == 0
    assert resources.update_calls == 0


@pytest.mark.asyncio
async def test_ensure_resource_migrates_canonical_to_local(hass, monkeypatch) -> None:
    from types import SimpleNamespace

    resources = _FakeResources(
        [
            {
                CONF_ID: "canonical",
                CONF_TYPE: "module",
                "url": f"{CARD_CANONICAL_BASE_URL}?v=old",
            }
        ]
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(resources=resources)

    async def _fake_cache_key(_hass):
        return "2.2.0-999"

    monkeypatch.setattr(frontend, "_cache_key_for_dev", _fake_cache_key)

    ok = await frontend._async_ensure_card_resource(hass)

    assert ok is True
    assert resources.update_calls == 1
    assert resources.async_items()[0]["url"] == f"{CARD_LEGACY_BASE_URL}?v=2.2.0-999"


@pytest.mark.asyncio
async def test_ensure_resource_falls_back_without_lovelace(hass, monkeypatch) -> None:
    async def _fake_cache_key(_hass):
        return "fallback"

    monkeypatch.setattr(frontend, "_cache_key_for_dev", _fake_cache_key)

    ok = await frontend._async_ensure_card_resource(hass)

    assert ok is False
