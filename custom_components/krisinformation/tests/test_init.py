"""Tests for the Krisinformation integration coordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock
import re

import pytest
from aiohttp import ClientError
from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.krisinformation.const import (
    DOMAIN,
    PRODUCTION_BASE_URL,
    INTEGRATION_VERSION,
    USER_AGENT_PRODUCT,
)


class TestCoordinatorSetup:
    """Test coordinator setup and lifecycle."""

    async def test_setup_entry_success(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test successful setup creates coordinator."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )

        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]

    async def test_unload_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test unload removes coordinator from hass.data."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert result is True
        assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})


class TestAPIRequests:
    """Test API request handling."""

    async def test_user_agent_header_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test User-Agent header includes integration and HA version."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )
        from homeassistant.const import __version__ as HA_VERSION

        mock_config_entry.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )

        headers = coordinator._build_headers()

        assert "User-Agent" in headers
        assert USER_AGENT_PRODUCT in headers["User-Agent"]
        assert INTEGRATION_VERSION in headers["User-Agent"]
        assert f"HomeAssistant/{HA_VERSION}" in headers["User-Agent"]

    async def test_accept_header(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test Accept header is application/json."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )

        headers = coordinator._build_headers()

        assert headers["Accept"] == "application/json"

    async def test_geocode_included_for_municipality(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test geocode parameter is included for specific municipality."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )

        url, params = coordinator._compose_url_and_params()

        # Stockholm should have a geocode
        assert "geocode" in params
        assert params["geocode"] != ""

    async def test_no_geocode_for_hela_sverige(
        self,
        hass: HomeAssistant,
        mock_config_entry_hela_sverige: MockConfigEntry,
    ) -> None:
        """Test no geocode parameter for 'Hela Sverige'."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry_hela_sverige.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry_hela_sverige, timedelta(seconds=300)
        )

        url, params = coordinator._compose_url_and_params()

        # Hela Sverige should not have geocode
        assert "geocode" not in params or params.get("geocode") == ""


class TestConditionalRequests:
    """Test ETag and Last-Modified conditional request handling."""

    async def test_etag_stored_from_response(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test ETag is stored from response headers."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
            headers={"ETag": '"test-etag-123"'},
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        assert coordinator._etag == '"test-etag-123"'

    async def test_last_modified_stored_from_response(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test Last-Modified is stored from response headers."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
            headers={"Last-Modified": "Mon, 15 Jan 2024 10:00:00 GMT"},
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        assert coordinator._last_modified == "Mon, 15 Jan 2024 10:00:00 GMT"

    async def test_if_none_match_header_sent(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test If-None-Match header sent when ETag is stored."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )
        coordinator._etag = '"stored-etag"'

        headers = coordinator._build_headers()

        assert "If-None-Match" in headers
        assert headers["If-None-Match"] == '"stored-etag"'

    async def test_if_modified_since_header_sent(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test If-Modified-Since header sent when Last-Modified is stored."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )
        coordinator._last_modified = "Mon, 15 Jan 2024 10:00:00 GMT"

        headers = coordinator._build_headers()

        assert "If-Modified-Since" in headers
        assert headers["If-Modified-Since"] == "Mon, 15 Jan 2024 10:00:00 GMT"

    async def test_304_not_modified_returns_cached_data(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test 304 response returns previously cached data."""
        # First request returns data
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=single_alert_response,
            headers={"ETag": '"etag-1"'},
        )
        # Second request returns 304
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            status=304,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        initial_data = coordinator.data
        assert initial_data is not None

        # Trigger refresh that gets 304
        await coordinator.async_refresh()

        # Data should be unchanged
        assert coordinator.data == initial_data


class TestRateLimiting:
    """Test 429 rate limiting handling."""

    async def test_429_increases_update_interval(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test 429 response increases the update interval."""
        # First request succeeds
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )
        # Second request rate limited
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            status=429,
            headers={"Retry-After": "600"},
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        original_interval = coordinator.update_interval

        await coordinator.async_refresh()

        # Interval should have increased
        assert coordinator.update_interval > original_interval

    async def test_429_max_interval_capped(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test 429 response caps interval at 900 seconds."""
        # First request succeeds
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )
        # Multiple 429 responses to test cap
        for _ in range(10):
            mock_aiohttp.get(
                re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
                status=429,
            )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Trigger multiple 429s
        for _ in range(5):
            await coordinator.async_refresh()

        # Interval should be capped at 900 seconds
        assert coordinator.update_interval.total_seconds() <= 900


class TestCacheControl:
    """Test Cache-Control header handling."""

    async def test_cache_control_max_age_updates_interval(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test max-age value updates the update interval."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
            headers={"Cache-Control": "max-age=180"},
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Interval should be set to 180 seconds
        assert coordinator.update_interval.total_seconds() == 180

    async def test_cache_control_max_age_min_bound(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test max-age below 60 is bounded to 60."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
            headers={"Cache-Control": "max-age=30"},
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Interval should be bounded at minimum 60 seconds
        assert coordinator.update_interval.total_seconds() >= 60

    async def test_cache_control_max_age_max_bound(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test max-age above 600 is bounded to 600."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
            headers={"Cache-Control": "max-age=1000"},
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]

        # Interval should be bounded at maximum 600 seconds
        assert coordinator.update_interval.total_seconds() <= 600


class TestDataNormalization:
    """Test data normalization and sanitization."""

    async def test_sanitize_text_crlf_normalized(self) -> None:
        """Test CRLF is normalized to single spaces."""
        from custom_components.krisinformation import _sanitize_text

        result = _sanitize_text("Line one\r\nLine two")

        assert "\r\n" not in result
        assert result == "Line one Line two"

    async def test_sanitize_text_whitespace_collapsed(self) -> None:
        """Test multiple whitespace collapsed to single space."""
        from custom_components.krisinformation import _sanitize_text

        result = _sanitize_text("Word    multiple   spaces")

        assert "    " not in result
        assert result == "Word multiple spaces"

    async def test_sanitize_text_none_preserved(self) -> None:
        """Test None values are preserved."""
        from custom_components.krisinformation import _sanitize_text

        result = _sanitize_text(None)

        assert result is None

    async def test_normalize_selects_correct_language(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test normalization selects correct language info block."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )

        normalized = coordinator._normalize_data(single_alert_response, "sv-SE")

        assert len(normalized) == 1
        assert normalized[0]["info"]["language"] == "sv-SE"
        assert "Test VMA" in normalized[0]["info"]["headline"]

    async def test_normalize_fallback_to_first_language(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test normalization falls back to first info if language not found."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )

        # Request non-existent language
        normalized = coordinator._normalize_data(single_alert_response, "de-DE")

        assert len(normalized) == 1
        # Should fall back to first info (sv-SE)
        assert normalized[0]["info"]["language"] == "sv-SE"


class TestFiltering:
    """Test alert filtering functionality."""

    async def test_filter_excludes_update_cancel_by_default(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        update_cancel_response: dict[str, Any],
    ) -> None:
        """Test Update and Cancel message types are excluded by default."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )

        normalized = coordinator._normalize_data(update_cancel_response, "sv-SE")
        filters = coordinator._get_filters()
        filtered = coordinator._apply_filters(normalized, filters)

        # Both Update and Cancel should be filtered out
        assert len(filtered) == 0

    async def test_filter_includes_update_cancel_when_enabled(
        self,
        hass: HomeAssistant,
        mock_config_entry_include_updates: MockConfigEntry,
        update_cancel_response: dict[str, Any],
    ) -> None:
        """Test Update and Cancel included when option enabled."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry_include_updates.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry_include_updates, timedelta(seconds=300)
        )

        normalized = coordinator._normalize_data(update_cancel_response, "sv-SE")
        filters = coordinator._get_filters()
        filtered = coordinator._apply_filters(normalized, filters)

        # Both should be included
        assert len(filtered) == 2

    async def test_filter_severity_minimum(
        self,
        hass: HomeAssistant,
        mock_config_entry_severity_severe: MockConfigEntry,
        multiple_alerts_response: dict[str, Any],
    ) -> None:
        """Test severity filtering excludes lower severities."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        mock_config_entry_severity_severe.add_to_hass(hass)
        session = MagicMock()

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry_severity_severe, timedelta(seconds=300)
        )

        normalized = coordinator._normalize_data(multiple_alerts_response, "sv-SE")
        filters = coordinator._get_filters()
        filtered = coordinator._apply_filters(normalized, filters)

        # Only Severe and Extreme should remain (Minor and Moderate excluded)
        severities = [a["info"]["severity"] for a in filtered]
        assert "Minor" not in severities
        assert "Moderate" not in severities
        assert "Severe" in severities
        assert "Extreme" in severities


class TestErrorHandling:
    """Test error handling."""

    async def test_client_error_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test ClientError raises UpdateFailed."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            exception=ClientError("Connection failed"),
        )

        mock_config_entry.add_to_hass(hass)

        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(hass)
        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    async def test_server_error_raises_update_failed(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test 500 server error raises UpdateFailed."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            status=500,
        )

        mock_config_entry.add_to_hass(hass)

        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )
        from homeassistant.helpers.aiohttp_client import async_get_clientsession

        session = async_get_clientsession(hass)
        coordinator = KrisinformationDataUpdateCoordinator(
            hass, session, mock_config_entry, timedelta(seconds=300)
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


class TestEvents:
    """Test event emission."""

    async def test_new_alert_event_fired(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test krisinformation_new_alert event fired for new alerts."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=single_alert_response,
        )

        events = []

        def capture_event(event):
            events.append(event)

        hass.bus.async_listen("krisinformation_new_alert", capture_event)

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert len(events) == 1
        assert events[0].data["identifier"] == "alert-001"
