"""Data coordinators for Krisinformation content sources."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KrisinformationApiClient, KrisinformationApiError
from .const import (
    CONF_LANGUAGE,
    CONF_INCLUDE_NATIONAL,
    CONF_INCLUDE_NEWS,
    CONF_INCLUDE_NOTICES,
    CONF_INCLUDE_UNLOCATED,
    CONF_MAX_ITEMS,
    CONF_MUNICIPALITY,
    CONF_NEWS_DAYS,
    INCLUDE_NATIONAL_DEFAULT,
    INCLUDE_NEWS_DEFAULT,
    INCLUDE_NOTICES_DEFAULT,
    INCLUDE_UNLOCATED_DEFAULT,
    LANGUAGE_DEFAULT,
    MAX_ITEMS_DEFAULT,
    MUNICIPALITY_DEFAULT,
    NEWS_DEFAULT_DAYS,
    NEWS_UPDATE_INTERVAL_SECONDS,
    NOTICES_UPDATE_INTERVAL_SECONDS,
)
from .helpers import county_code_for_location, content_matches_geography
from .models import NewsItem, NoticeItem

_LOGGER = logging.getLogger(__name__)


def _entry_option(entry: ConfigEntry, key: str, default: Any) -> Any:
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
        if not _entry_option(self._entry, CONF_INCLUDE_NEWS, INCLUDE_NEWS_DEFAULT):
            return ()
        location = self._entry.data.get(CONF_MUNICIPALITY, MUNICIPALITY_DEFAULT)
        county_code = county_code_for_location(location)
        try:
            items = await self._client.async_get_news(
                language=_entry_option(self._entry, CONF_LANGUAGE, LANGUAGE_DEFAULT),
                county_codes=(county_code,) if county_code else None,
                all_counties=county_code is None,
                days=_entry_option(self._entry, CONF_NEWS_DAYS, NEWS_DEFAULT_DAYS),
            )
        except KrisinformationApiError as err:
            raise UpdateFailed(f"Unable to update Krisinformation news: {err}") from err
        filtered = (
            item
            for item in items
            if content_matches_geography(
                item.areas,
                location,
                include_national=_entry_option(
                    self._entry, CONF_INCLUDE_NATIONAL, INCLUDE_NATIONAL_DEFAULT
                ),
                include_unlocated=_entry_option(
                    self._entry, CONF_INCLUDE_UNLOCATED, INCLUDE_UNLOCATED_DEFAULT
                ),
            )
        )
        return tuple(filtered)[
            : _entry_option(self._entry, CONF_MAX_ITEMS, MAX_ITEMS_DEFAULT)
        ]


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
        if not _entry_option(
            self._entry, CONF_INCLUDE_NOTICES, INCLUDE_NOTICES_DEFAULT
        ):
            return ()
        location = self._entry.data.get(CONF_MUNICIPALITY, MUNICIPALITY_DEFAULT)
        county_code = county_code_for_location(location)
        try:
            items = await self._client.async_get_notices(
                language=_entry_option(self._entry, CONF_LANGUAGE, LANGUAGE_DEFAULT),
                county_codes=(county_code,) if county_code else None,
                all_counties=county_code is None,
            )
        except KrisinformationApiError as err:
            raise UpdateFailed(
                f"Unable to update Krisinformation notices: {err}"
            ) from err
        filtered = (
            item
            for item in items
            if content_matches_geography(
                item.areas,
                location,
                include_national=_entry_option(
                    self._entry, CONF_INCLUDE_NATIONAL, INCLUDE_NATIONAL_DEFAULT
                ),
                include_unlocated=_entry_option(
                    self._entry, CONF_INCLUDE_UNLOCATED, INCLUDE_UNLOCATED_DEFAULT
                ),
            )
        )
        return tuple(filtered)[
            : _entry_option(self._entry, CONF_MAX_ITEMS, MAX_ITEMS_DEFAULT)
        ]
