"""Tests for the Krisinformation binary sensor platform."""

from __future__ import annotations

import re
from typing import Any
from unittest.mock import MagicMock

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.krisinformation.const import PRODUCTION_BASE_URL


class TestBinarySensorSetup:
    """Test binary sensor setup."""

    async def test_binary_sensor_created_on_setup(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test binary sensor entity is created when entry is set up."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Check binary sensor exists
        states = hass.states.async_all("binary_sensor")
        krisinformation_binary_sensors = [
            s for s in states if "krisinformation" in s.entity_id.lower()
        ]

        assert len(krisinformation_binary_sensors) >= 1


class TestBinarySensorState:
    """Test binary sensor state."""

    async def test_binary_sensor_off_without_alerts(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        empty_response: dict[str, Any],
    ) -> None:
        """Test binary sensor is OFF when no alerts."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=empty_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Find the binary sensor
        states = hass.states.async_all("binary_sensor")
        binary_sensor = None
        for state in states:
            if "krisinformation" in state.entity_id.lower():
                binary_sensor = state
                break

        assert binary_sensor is not None
        assert binary_sensor.state == "off"

    async def test_binary_sensor_on_with_alerts(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test binary sensor is ON when alerts present."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=single_alert_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Find the binary sensor
        states = hass.states.async_all("binary_sensor")
        binary_sensor = None
        for state in states:
            if "krisinformation" in state.entity_id.lower():
                binary_sensor = state
                break

        assert binary_sensor is not None
        assert binary_sensor.state == "on"


class TestBinarySensorProperties:
    """Test binary sensor properties."""

    async def test_binary_sensor_unique_id(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test binary sensor unique_id follows expected pattern."""
        from custom_components.krisinformation.binary_sensor import (
            KrisinformationActiveBinary,
        )

        mock_config_entry.add_to_hass(hass)

        coordinator = MagicMock()
        coordinator.config = mock_config_entry.data
        coordinator.data = {"alerts": []}

        binary_sensor = KrisinformationActiveBinary(
            mock_config_entry.entry_id, coordinator
        )

        unique_id = binary_sensor.unique_id

        assert unique_id == f"krisinformation_{mock_config_entry.entry_id}_vma_active"

    async def test_binary_sensor_device_class(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test binary sensor has safety device class."""
        from custom_components.krisinformation.binary_sensor import (
            KrisinformationActiveBinary,
        )
        from homeassistant.components.binary_sensor import BinarySensorDeviceClass

        mock_config_entry.add_to_hass(hass)

        coordinator = MagicMock()
        coordinator.config = mock_config_entry.data
        coordinator.data = {"alerts": []}

        binary_sensor = KrisinformationActiveBinary(
            mock_config_entry.entry_id, coordinator
        )

        # Check device_class is the SAFETY enum
        assert binary_sensor._attr_device_class == BinarySensorDeviceClass.SAFETY

    async def test_binary_sensor_name_contains_vma(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test binary sensor name contains 'VMA'."""
        from custom_components.krisinformation.binary_sensor import (
            KrisinformationActiveBinary,
        )

        mock_config_entry.add_to_hass(hass)

        coordinator = MagicMock()
        coordinator.config = mock_config_entry.data
        coordinator.data = {"alerts": []}

        binary_sensor = KrisinformationActiveBinary(
            mock_config_entry.entry_id, coordinator
        )

        name = binary_sensor.name

        assert "VMA" in name
        assert "Stockholm" in name


class TestBinarySensorAttributes:
    """Test binary sensor attributes."""

    async def test_binary_sensor_alerts_attribute(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
        mock_aiohttp: aioresponses,
        single_alert_response: dict[str, Any],
    ) -> None:
        """Test binary sensor has alerts attribute."""
        mock_aiohttp.get(
            re.compile(rf"^{re.escape(PRODUCTION_BASE_URL)}.*"),
            payload=single_alert_response,
        )

        mock_config_entry.add_to_hass(hass)

        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        # Find the binary sensor
        states = hass.states.async_all("binary_sensor")
        binary_sensor = None
        for state in states:
            if "krisinformation" in state.entity_id.lower():
                binary_sensor = state
                break

        assert binary_sensor is not None
        assert "alerts" in binary_sensor.attributes
        alerts = binary_sensor.attributes["alerts"]
        assert isinstance(alerts, list)
        assert len(alerts) == 1


class TestBinarySensorDeviceInfo:
    """Test binary sensor device info."""

    async def test_binary_sensor_device_info(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test binary sensor provides correct device info."""
        from custom_components.krisinformation.binary_sensor import (
            KrisinformationActiveBinary,
        )
        from custom_components.krisinformation.const import (
            DEVICE_MANUFACTURER,
            DEVICE_MODEL,
        )

        mock_config_entry.add_to_hass(hass)

        coordinator = MagicMock()
        coordinator.config = mock_config_entry.data
        coordinator.data = {"alerts": []}

        binary_sensor = KrisinformationActiveBinary(
            mock_config_entry.entry_id, coordinator
        )

        device_info = binary_sensor.device_info

        assert "identifiers" in device_info
        assert device_info["manufacturer"] == DEVICE_MANUFACTURER
        assert device_info["model"] == DEVICE_MODEL

    async def test_binary_sensor_same_device_as_sensor(
        self,
        hass: HomeAssistant,
        mock_config_entry: MockConfigEntry,
    ) -> None:
        """Test binary sensor and sensor share same device."""
        from custom_components.krisinformation.binary_sensor import (
            KrisinformationActiveBinary,
        )
        from custom_components.krisinformation.sensor import KrisinformationCountSensor

        mock_config_entry.add_to_hass(hass)

        coordinator = MagicMock()
        coordinator.config = mock_config_entry.data
        coordinator.data = {"alerts": []}

        binary_sensor = KrisinformationActiveBinary(
            mock_config_entry.entry_id, coordinator
        )
        sensor = KrisinformationCountSensor(mock_config_entry.entry_id, coordinator)

        # Device identifiers should match
        assert (
            binary_sensor.device_info["identifiers"]
            == sensor.device_info["identifiers"]
        )
