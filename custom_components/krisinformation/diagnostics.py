from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


TO_REDACT = {"contact"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    runtime_data = entry.runtime_data
    vma = runtime_data.vma_coordinator
    news = runtime_data.news_coordinator
    notices = runtime_data.notices_coordinator

    def coordinator_info(coordinator, data: Any) -> dict[str, Any]:
        return {
            "last_success": coordinator.last_update_success,
            "update_interval": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
            "data": data,
        }

    return {
        "config": async_redact_data(dict(entry.data), TO_REDACT),
        "options": async_redact_data(dict(entry.options), TO_REDACT),
        "sources": async_redact_data(
            {
                "vma": coordinator_info(vma, vma.data or {}),
                "news": coordinator_info(
                    news, [item.as_dict() for item in (news.data or ())]
                ),
                "notices": coordinator_info(
                    notices, [item.as_dict() for item in (notices.data or ())]
                ),
            },
            TO_REDACT,
        ),
    }
