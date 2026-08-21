"""Tests for the Krisinformation config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.krisinformation.const import (
    DOMAIN,
    CONF_NAME,
    CONF_MUNICIPALITY,
    CONF_LANGUAGE,
    CONF_INCLUDE_UPDATE_CANCEL,
    CONF_SEVERITY_MIN,
    CONF_API_ENV,
    CONF_INCLUDE_NATIONAL,
    CONF_INCLUDE_NEWS,
    CONF_INCLUDE_NOTICES,
    CONF_INCLUDE_SMHI_WEATHER_WARNINGS,
    CONF_INCLUDE_UNLOCATED,
    CONF_MAX_ITEMS,
    CONF_NEWS_DAYS,
    LANGUAGE_DEFAULT,
    INCLUDE_UPDATE_CANCEL_DEFAULT,
    SEVERITY_MIN_DEFAULT,
    API_ENV_PRODUCTION,
    API_ENV_TEST,
)


class TestUserStep:
    """Test user step of config flow."""

    async def test_user_step_shows_form(self, hass: HomeAssistant) -> None:
        """Test that user step shows form."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    async def test_user_step_creates_entry(self, hass: HomeAssistant) -> None:
        """Test user step creates config entry with valid input."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.krisinformation.async_setup_entry",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_NAME: "My Alerts",
                    CONF_MUNICIPALITY: "Stockholm",
                },
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "reload_notice"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "My Alerts (Stockholm)"
        assert result["data"][CONF_NAME] == "My Alerts"
        assert result["data"][CONF_MUNICIPALITY] == "Stockholm"
        assert result["options"][CONF_INCLUDE_NEWS] is True
        assert result["options"][CONF_INCLUDE_NOTICES] is True
        assert result["options"][CONF_INCLUDE_SMHI_WEATHER_WARNINGS] is True
        assert result["options"][CONF_NEWS_DAYS] == 7
        assert result["options"][CONF_MAX_ITEMS] == 10

    async def test_user_step_default_name(self, hass: HomeAssistant) -> None:
        """Test user step uses default name when not provided."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.krisinformation.async_setup_entry",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_MUNICIPALITY: "Göteborg",
                },
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "reload_notice"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert "Krisinformation" in result["title"]

    async def test_user_step_hela_sverige(self, hass: HomeAssistant) -> None:
        """Test user step with 'Hela Sverige' municipality."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.krisinformation.async_setup_entry",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_NAME: "All Sweden",
                    CONF_MUNICIPALITY: "Hela Sverige",
                },
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "reload_notice"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_MUNICIPALITY] == "Hela Sverige"

    async def test_user_step_with_all_options(self, hass: HomeAssistant) -> None:
        """Test user step with all optional fields."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        with patch(
            "custom_components.krisinformation.async_setup_entry",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_NAME: "Custom Name",
                    CONF_MUNICIPALITY: "Malmö",
                    CONF_LANGUAGE: "en-US",
                    CONF_INCLUDE_UPDATE_CANCEL: True,
                    CONF_SEVERITY_MIN: "Severe",
                    CONF_API_ENV: API_ENV_TEST,
                    CONF_INCLUDE_NEWS: True,
                    CONF_INCLUDE_NOTICES: False,
                    CONF_INCLUDE_SMHI_WEATHER_WARNINGS: False,
                    CONF_NEWS_DAYS: 14,
                    CONF_MAX_ITEMS: 20,
                    CONF_INCLUDE_NATIONAL: False,
                    CONF_INCLUDE_UNLOCATED: False,
                },
            )

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "reload_notice"
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {}
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["options"][CONF_LANGUAGE] == "en-US"
        assert result["options"][CONF_INCLUDE_UPDATE_CANCEL] is True
        assert result["options"][CONF_SEVERITY_MIN] == "Severe"
        assert result["options"][CONF_API_ENV] == API_ENV_TEST
        assert result["options"][CONF_INCLUDE_NOTICES] is False
        assert result["options"][CONF_INCLUDE_SMHI_WEATHER_WARNINGS] is False
        assert result["options"][CONF_NEWS_DAYS] == 14
        assert result["options"][CONF_MAX_ITEMS] == 20
        assert result["options"][CONF_INCLUDE_NATIONAL] is False
        assert result["options"][CONF_INCLUDE_UNLOCATED] is False


class TestOptionsFlow:
    """Test options flow."""

    async def test_options_flow_shows_form(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test options flow shows form with current values."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_saves_options(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test options flow saves updated options."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_LANGUAGE: "en-US",
                CONF_SEVERITY_MIN: "Severe",
                CONF_INCLUDE_UPDATE_CANCEL: True,
                CONF_API_ENV: API_ENV_PRODUCTION,
                CONF_INCLUDE_NEWS: False,
                CONF_INCLUDE_NOTICES: True,
                CONF_INCLUDE_SMHI_WEATHER_WARNINGS: False,
                CONF_NEWS_DAYS: 14,
                CONF_MAX_ITEMS: 25,
                CONF_INCLUDE_NATIONAL: False,
                CONF_INCLUDE_UNLOCATED: True,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert mock_config_entry.options[CONF_LANGUAGE] == "en-US"
        assert mock_config_entry.options[CONF_SEVERITY_MIN] == "Severe"
        assert mock_config_entry.options[CONF_INCLUDE_UPDATE_CANCEL] is True
        assert mock_config_entry.options[CONF_INCLUDE_NEWS] is False
        assert mock_config_entry.options[CONF_INCLUDE_SMHI_WEATHER_WARNINGS] is False
        assert mock_config_entry.options[CONF_NEWS_DAYS] == 14
        assert mock_config_entry.options[CONF_MAX_ITEMS] == 25

    async def test_options_flow_change_language(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test changing language in options."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_LANGUAGE: "en-US",
                CONF_SEVERITY_MIN: SEVERITY_MIN_DEFAULT,
                CONF_INCLUDE_UPDATE_CANCEL: INCLUDE_UPDATE_CANCEL_DEFAULT,
                CONF_API_ENV: API_ENV_PRODUCTION,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert mock_config_entry.options[CONF_LANGUAGE] == "en-US"

    async def test_options_flow_change_api_env(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test changing API environment in options."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_LANGUAGE: LANGUAGE_DEFAULT,
                CONF_SEVERITY_MIN: SEVERITY_MIN_DEFAULT,
                CONF_INCLUDE_UPDATE_CANCEL: INCLUDE_UPDATE_CANCEL_DEFAULT,
                CONF_API_ENV: API_ENV_TEST,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert mock_config_entry.options[CONF_API_ENV] == API_ENV_TEST


class TestReconfigureStep:
    """Test reconfigure step."""

    async def test_reconfigure_shows_form(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test reconfigure step shows form."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": mock_config_entry.entry_id,
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

    async def test_reconfigure_updates_entry(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test reconfigure step updates entry data and options."""
        mock_config_entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": mock_config_entry.entry_id,
            },
        )

        with patch(
            "custom_components.krisinformation.async_setup_entry",
            return_value=True,
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {
                    CONF_NAME: "Updated Name",
                    CONF_MUNICIPALITY: "Göteborg",
                    CONF_LANGUAGE: "en-US",
                    CONF_SEVERITY_MIN: "Moderate",
                    CONF_INCLUDE_UPDATE_CANCEL: True,
                    CONF_API_ENV: API_ENV_TEST,
                },
            )

        # Should abort with reconfigured reason (reload triggered)
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reconfigured"

        # Check data was updated
        assert mock_config_entry.data[CONF_NAME] == "Updated Name"
        assert mock_config_entry.data[CONF_MUNICIPALITY] == "Göteborg"

        # Check options were updated
        assert mock_config_entry.options[CONF_LANGUAGE] == "en-US"
        assert mock_config_entry.options[CONF_SEVERITY_MIN] == "Moderate"


class TestConfigFlowStaticMethod:
    """Test that async_get_options_flow is properly defined."""

    async def test_async_get_options_flow_returns_handler(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test async_get_options_flow returns OptionsFlowHandler."""
        from custom_components.krisinformation.config_flow import (
            ConfigFlow,
            OptionsFlowHandler,
        )

        result = ConfigFlow.async_get_options_flow(mock_config_entry)

        assert isinstance(result, OptionsFlowHandler)
