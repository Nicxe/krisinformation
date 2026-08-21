"""Data coordinators for Krisinformation content sources."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KrisinformationApiClient, KrisinformationApiError
from .const import (
    CONF_LANGUAGE,
    LANGUAGE_DEFAULT,
    NEWS_DEFAULT_DAYS,
    NEWS_UPDATE_INTERVAL_SECONDS,
    NOTICES_UPDATE_INTERVAL_SECONDS,
)
from .models import NewsItem, NoticeItem

_LOGGER = logging.getLogger(__name__)


def _entry_option(entry: ConfigEntry, key: str, default: str) -> str:
    """Read an option while supporting entries created by older releases."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, default)


class KrisinformationNewsCoordinator(DataUpdateCoordinator[tuple[NewsItem, ...]]):
    """Update Krisinformation news independently from other sources."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: KrisinformationApiClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Krisinformation news",
            update_interval=timedelta(seconds=NEWS_UPDATE_INTERVAL_SECONDS),
            config_entry=entry,
        )
        self._client = client
        self._entry = entry

    async def _async_update_data(self) -> tuple[NewsItem, ...]:
        try:
            return await self._client.async_get_news(
                language=_entry_option(self._entry, CONF_LANGUAGE, LANGUAGE_DEFAULT),
                all_counties=True,
                days=NEWS_DEFAULT_DAYS,
            )
        except KrisinformationApiError as err:
            raise UpdateFailed(f"Unable to update Krisinformation news: {err}") from err


class KrisinformationNoticesCoordinator(DataUpdateCoordinator[tuple[NoticeItem, ...]]):
    """Update Krisinformation notices independently from other sources."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: KrisinformationApiClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Krisinformation notices",
            update_interval=timedelta(seconds=NOTICES_UPDATE_INTERVAL_SECONDS),
            config_entry=entry,
        )
        self._client = client
        self._entry = entry

    async def _async_update_data(self) -> tuple[NoticeItem, ...]:
        try:
            return await self._client.async_get_notices(
                language=_entry_option(self._entry, CONF_LANGUAGE, LANGUAGE_DEFAULT),
                all_counties=True,
            )
        except KrisinformationApiError as err:
            raise UpdateFailed(
                f"Unable to update Krisinformation notices: {err}"
            ) from err
