"""Tests for the Krisinformation integration coordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch
import re

import pytest
from aiohttp import ClientError
from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import UpdateFailed

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.krisinformation.const import (
    DOMAIN,
    PRODUCTION_BASE_URL,
    INTEGRATION_VERSION,
    USER_AGENT_PRODUCT,
)


@pytest.mark.parametrize("device_exists", [True, False])
async def test_device_migration_uses_config_entry_scoped_lookup(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    device_exists: bool,
) -> None:
    """Use the scoped API without calling the deprecated global lookup."""
    from custom_components.krisinformation import _async_migrate_registry_identifiers

    mock_config_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    identifier = (DOMAIN, f"stockholm_{mock_config_entry.entry_id}")
    extra_identifier = (DOMAIN, "additional_identifier")
    device = registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={identifier, extra_identifier},
    )

    with (
        patch.object(
            registry,
            "async_get_device_by_identifier",
            return_value=device if device_exists else None,
            create=True,
        ) as scoped_lookup,
        patch.object(
            registry,
            "async_get_device",
            side_effect=AssertionError("Deprecated device lookup must not be used"),
            create=True,
        ),
    ):
        await _async_migrate_registry_identifiers(hass, mock_config_entry)

    scoped_lookup.assert_called_once_with(identifier, mock_config_entry.entry_id)
    updated = registry.async_get(device.id)
    assert updated is not None
    assert updated.identifiers == {
        (DOMAIN, f"{mock_config_entry.entry_id}_vma") if device_exists else identifier,
        extra_identifier,
    }


@pytest.mark.parametrize("device_owned_by_entry", [True, False])
async def test_device_migration_compatibility_is_scoped_to_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    device_owned_by_entry: bool,
) -> None:
    """The compatibility lookup must only migrate devices owned by this entry."""
    from custom_components.krisinformation import _async_migrate_registry_identifiers

    mock_config_entry.add_to_hass(hass)
    other_entry = MockConfigEntry(domain=DOMAIN, entry_id="other_entry")
    other_entry.add_to_hass(hass)
    registry = dr.async_get(hass)
    identifier = (DOMAIN, f"stockholm_{mock_config_entry.entry_id}")
    other_device = registry.async_get_or_create(
        config_entry_id=(
            mock_config_entry.entry_id
            if device_owned_by_entry
            else other_entry.entry_id
        ),
        identifiers={identifier},
    )

    with patch.object(registry, "async_get_device_by_identifier", None, create=True):
        await _async_migrate_registry_identifiers(hass, mock_config_entry)

    updated = registry.async_get(other_device.id)
    assert updated is not None
    assert updated.identifiers == {
        (DOMAIN, f"{mock_config_entry.entry_id}_vma")
        if device_owned_by_entry
        else identifier
    }


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
        assert mock_config_entry.runtime_data.vma_coordinator is not None
        assert mock_config_entry.runtime_data.api_client is not None
        assert mock_config_entry.runtime_data.news_coordinator is not None
        assert mock_config_entry.runtime_data.notices_coordinator is not None
        assert (
            mock_config_entry.runtime_data.vma_coordinator.update_interval
            == timedelta(seconds=60)
        )

    async def test_unload_entry(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test unload releases runtime data."""
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
        assert not hasattr(mock_config_entry, "runtime_data")

    async def test_legacy_registry_identifiers_are_migrated(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test existing entity IDs and devices survive stable-ID migration."""
        from homeassistant.helpers import device_registry as dr
        from homeassistant.helpers import entity_registry as er

        mock_config_entry.add_to_hass(hass)
        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        legacy_device = device_registry.async_get_or_create(
            config_entry_id=mock_config_entry.entry_id,
            identifiers={(DOMAIN, f"stockholm_{mock_config_entry.entry_id}")},
        )
        legacy_entity = entity_registry.async_get_or_create(
            "sensor",
            DOMAIN,
            f"krisinformation_sensor_stockholm_{mock_config_entry.entry_id}",
            config_entry=mock_config_entry,
            device_id=legacy_device.id,
            suggested_object_id="krisinformation_stockholm",
        )
        original_entity_id = legacy_entity.entity_id
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        migrated_entity = entity_registry.async_get(original_entity_id)
        migrated_device = device_registry.async_get(legacy_device.id)
        assert migrated_entity is not None
        assert migrated_entity.unique_id == (
            f"krisinformation_{mock_config_entry.entry_id}_vma_count"
        )
        assert migrated_device is not None
        assert migrated_device.identifiers == {
            (DOMAIN, f"{mock_config_entry.entry_id}_vma")
        }


async def test_v3_entry_migrates_optional_settings_to_v5(
    hass: HomeAssistant,
) -> None:
    """Test existing optional values move out of config entry data."""
    from custom_components.krisinformation import async_migrate_entry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Legacy entry",
        data={
            "name": "Legacy",
            "municipality": "Göteborg",
            "language": "en-US",
            "api_environment": "test",
        },
        options={"severity_min": "Extreme"},
        entry_id="legacy_v3_entry",
        version=3,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is True

    assert entry.version == 5
    assert entry.data == {"name": "Legacy", "municipality": "Göteborg"}
    assert entry.options["language"] == "en-US"
    assert entry.options["api_environment"] == "test"
    assert entry.options["severity_min"] == "Extreme"
    assert entry.options["include_news"] is True
    assert entry.options["include_notices"] is True
    assert entry.options["include_smhi_weather_warnings"] is True
    assert entry.options["news_days"] == 7
    assert entry.options["max_items"] == 10
    assert entry.options["include_national"] is True
    assert entry.options["include_unlocated"] is True


async def test_v4_entry_migration_preserves_smhi_weather_warning_option(
    hass: HomeAssistant,
) -> None:
    """Test an explicitly disabled SMHI filter survives the v5 migration."""
    from custom_components.krisinformation import async_migrate_entry

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Krisinformation",
        data={"name": "Krisinformation", "municipality": "Stockholm"},
        options={"include_smhi_weather_warnings": False},
        entry_id="legacy_v4_entry",
        version=4,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is True

    assert entry.version == 5
    assert entry.options["include_smhi_weather_warnings"] is False


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


class TestRequestContract:
    """Test requests follow the documented SR VMA v3 contract."""

    async def test_request_uses_only_documented_headers(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test requests do not send unsupported conditional headers."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, MagicMock(), mock_config_entry, timedelta(seconds=300)
        )

        assert set(coordinator._build_headers()) == {"Accept", "User-Agent"}

    async def test_request_uses_only_documented_query_parameters(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test geocode is the only query parameter sent to SR."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, MagicMock(), mock_config_entry, timedelta(seconds=300)
        )

        _, params = coordinator._compose_url_and_params()

        assert set(params) == {"geocode"}


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
        coordinator = mock_config_entry.runtime_data.vma_coordinator

        original_interval = coordinator.update_interval

        await coordinator.async_refresh()

        # Interval should have increased
        assert coordinator.update_interval > original_interval
        assert coordinator.last_update_success is False

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
        coordinator = mock_config_entry.runtime_data.vma_coordinator

        # Trigger multiple 429s
        for _ in range(5):
            await coordinator.async_refresh()

        # Interval should be capped at 900 seconds
        assert coordinator.update_interval.total_seconds() <= 900


class TestPolling:
    """Test explicit polling behavior."""

    async def test_cache_control_does_not_override_polling_interval(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test the integration controls polling rather than response cache headers."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
            headers={"Cache-Control": "public,max-age=5"},
        )
        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        coordinator = mock_config_entry.runtime_data.vma_coordinator
        assert coordinator.update_interval == timedelta(seconds=60)


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

    async def test_production_excludes_test_and_exercise_messages(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test only actual public announcements are exposed in production."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, MagicMock(), mock_config_entry, timedelta(seconds=60)
        )
        normalized = coordinator._normalize_data(single_alert_response, "sv-SE")

        for status in ("Test", "Exercise"):
            normalized[0]["status"] = status
            assert (
                coordinator._apply_filters(normalized, coordinator._get_filters()) == []
            )

    async def test_test_environment_includes_test_messages(
        self,
        hass: HomeAssistant,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test the SR test environment remains useful for development."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"name": "Test", "municipality": "Hela Sverige"},
            options={"api_environment": "test"},
            entry_id="test_environment_entry",
            version=3,
        )
        coordinator = KrisinformationDataUpdateCoordinator(
            hass, MagicMock(), entry, timedelta(seconds=60)
        )
        normalized = coordinator._normalize_data(single_alert_response, "sv-SE")
        normalized[0]["status"] = "Test"

        assert coordinator._apply_filters(normalized, coordinator._get_filters())

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

    async def test_initial_snapshot_does_not_fire_events(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test existing alerts are not announced again during startup."""
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

        assert events == []

    async def test_new_alert_after_initial_snapshot_fires_event(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test alerts added after startup fire a new-alert event."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, MagicMock(), mock_config_entry, timedelta(seconds=60)
        )
        normalized = coordinator._normalize_data(single_alert_response, "sv-SE")
        events = []
        hass.bus.async_listen("krisinformation_new_alert", events.append)

        coordinator._emit_events([])
        coordinator._emit_events(normalized)
        await hass.async_block_till_done()

        assert [event.data["identifier"] for event in events] == ["alert-001"]

    async def test_update_and_cancel_use_incident_identifier(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        single_alert_response: dict[str, Any],
        update_cancel_response: dict[str, Any],
    ) -> None:
        """Test CAP identifiers can change while the VMA incident stays stable."""
        from custom_components.krisinformation import (
            KrisinformationDataUpdateCoordinator,
        )

        coordinator = KrisinformationDataUpdateCoordinator(
            hass, MagicMock(), mock_config_entry, timedelta(seconds=60)
        )
        initial = coordinator._normalize_data(single_alert_response, "sv-SE")
        lifecycle = coordinator._normalize_data(update_cancel_response, "sv-SE")
        canceled = {**lifecycle[1], "incidents": "incident-001"}
        updated_events = []
        canceled_events = []
        hass.bus.async_listen("krisinformation_updated_alert", updated_events.append)
        hass.bus.async_listen("krisinformation_canceled_alert", canceled_events.append)

        coordinator._emit_events(initial)
        coordinator._emit_events([lifecycle[0]])
        coordinator._emit_events([canceled])
        await hass.async_block_till_done()

        assert [event.data["identifier"] for event in updated_events] == [
            "alert-update-001"
        ]
        assert [event.data["identifier"] for event in canceled_events] == [
            "alert-cancel-002"
        ]
