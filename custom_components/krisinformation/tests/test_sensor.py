"""Tests for the Krisinformation sensor platform."""

from __future__ import annotations

import re
from typing import Any
from unittest.mock import MagicMock

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.krisinformation.const import DOMAIN, PRODUCTION_BASE_URL


class TestSensorSetup:
    """Test sensor setup."""

    async def test_sensor_created_on_setup(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test sensor entity is created when entry is set up."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Check sensor exists
        states = hass.states.async_all("sensor")
        krisinformation_sensors = [
            s for s in states if "krisinformation" in s.entity_id.lower()
        ]

        assert len(krisinformation_sensors) >= 1


class TestSensorState:
    """Test sensor state."""

    async def test_sensor_state_zero_alerts(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test sensor state is 0 when no alerts."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Find the count sensor
        states = hass.states.async_all("sensor")
        count_sensor = None
        for state in states:
            if "krisinformation" in state.entity_id.lower():
                count_sensor = state
                break

        assert count_sensor is not None
        assert int(count_sensor.state) == 0

    async def test_sensor_state_with_alerts(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test sensor state equals alert count."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=single_alert_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Find the count sensor
        states = hass.states.async_all("sensor")
        count_sensor = None
        for state in states:
            if "krisinformation" in state.entity_id.lower():
                count_sensor = state
                break

        assert count_sensor is not None
        assert int(count_sensor.state) == 1

    async def test_sensor_state_multiple_alerts(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        multiple_alerts_response: dict[str, Any],
    ) -> None:
        """Test sensor state with multiple alerts (filtered by default)."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=multiple_alerts_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Find the count sensor
        states = hass.states.async_all("sensor")
        count_sensor = None
        for state in states:
            if "krisinformation" in state.entity_id.lower():
                count_sensor = state
                break

        assert count_sensor is not None
        # All 4 alerts should pass filters (all are Alert type, all severities >= Minor)
        assert int(count_sensor.state) == 4


class TestSensorAttributes:
    """Test sensor attributes."""

    async def test_sensor_alerts_attribute(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test sensor has alerts attribute with alert list."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=single_alert_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Find the count sensor
        states = hass.states.async_all("sensor")
        count_sensor = None
        for state in states:
            if "krisinformation" in state.entity_id.lower():
                count_sensor = state
                break

        assert count_sensor is not None
        assert "alerts" in count_sensor.attributes
        alerts = count_sensor.attributes["alerts"]
        assert isinstance(alerts, list)
        assert len(alerts) == 1
        assert alerts[0]["identifier"] == "alert-001"


class TestSensorUniqueId:
    """Test sensor unique ID."""

    async def test_sensor_unique_id_format(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test sensor unique_id follows expected pattern."""
        from custom_components.krisinformation.sensor import KrisinformationCountSensor

        mock_config_entry.add_to_hass(hass)

        # Create a mock coordinator
        coordinator = MagicMock()
        coordinator.config = mock_config_entry.data
        coordinator.data = {"alerts": []}

        sensor = KrisinformationCountSensor(mock_config_entry.entry_id, coordinator)

        unique_id = sensor.unique_id

        assert unique_id.startswith("krisinformation_sensor_")
        assert mock_config_entry.entry_id in unique_id

    async def test_sensor_unique_id_sanitizes_swedish_chars(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test unique_id sanitizes Swedish characters."""
        from custom_components.krisinformation.sensor import KrisinformationCountSensor

        # Create entry with Swedish municipality name
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"name": "Test", "municipality": "Malmö"},
            entry_id="test_malmo",
            version=3,
        )
        entry.add_to_hass(hass)

        coordinator = MagicMock()
        coordinator.config = entry.data
        coordinator.data = {"alerts": []}

        sensor = KrisinformationCountSensor(entry.entry_id, coordinator)

        unique_id = sensor.unique_id

        # Swedish ö should be replaced with o
        assert "ö" not in unique_id
        assert "malmo" in unique_id


class TestSensorDeviceInfo:
    """Test sensor device info."""

    async def test_sensor_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test sensor provides correct device info."""
        from custom_components.krisinformation.sensor import KrisinformationCountSensor
        from custom_components.krisinformation.const import (
            DEVICE_MANUFACTURER,
            DEVICE_MODEL,
        )

        mock_config_entry.add_to_hass(hass)

        coordinator = MagicMock()
        coordinator.config = mock_config_entry.data
        coordinator.data = {"alerts": []}

        sensor = KrisinformationCountSensor(mock_config_entry.entry_id, coordinator)

        device_info = sensor.device_info

        assert "identifiers" in device_info
        assert device_info["manufacturer"] == DEVICE_MANUFACTURER
        assert device_info["model"] == DEVICE_MODEL
        assert "Stockholm" in device_info["name"]
