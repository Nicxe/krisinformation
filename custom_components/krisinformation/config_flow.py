"""Config flow for the Krisinformation integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    API_ENV_PRODUCTION,
    API_ENV_TEST,
    CONF_API_ENV,
    CONF_INCLUDE_NATIONAL,
    CONF_INCLUDE_NEWS,
    CONF_INCLUDE_NOTICES,
    CONF_INCLUDE_SMHI_WEATHER_WARNINGS,
    CONF_INCLUDE_UNLOCATED,
    CONF_INCLUDE_UPDATE_CANCEL,
    CONF_LANGUAGE,
    CONF_MAX_ITEMS,
    CONF_MUNICIPALITY,
    CONF_NEWS_DAYS,
    CONF_SEVERITY_MIN,
    DOMAIN,
    INCLUDE_NATIONAL_DEFAULT,
    INCLUDE_NEWS_DEFAULT,
    INCLUDE_NOTICES_DEFAULT,
    INCLUDE_SMHI_WEATHER_WARNINGS_DEFAULT,
    INCLUDE_UNLOCATED_DEFAULT,
    INCLUDE_UPDATE_CANCEL_DEFAULT,
    LANGUAGE_DEFAULT,
    MAX_ITEMS_DEFAULT,
    MUNICIPALITY_DEFAULT,
    MUNICIPALITY_OPTIONS,
    NEWS_DEFAULT_DAYS,
    SEVERITY_MIN_DEFAULT,
)

_OPTION_DEFAULTS: dict[str, Any] = {
    CONF_LANGUAGE: LANGUAGE_DEFAULT,
    CONF_INCLUDE_UPDATE_CANCEL: INCLUDE_UPDATE_CANCEL_DEFAULT,
    CONF_SEVERITY_MIN: SEVERITY_MIN_DEFAULT,
    CONF_API_ENV: API_ENV_PRODUCTION,
    CONF_INCLUDE_NEWS: INCLUDE_NEWS_DEFAULT,
    CONF_INCLUDE_NOTICES: INCLUDE_NOTICES_DEFAULT,
    CONF_INCLUDE_SMHI_WEATHER_WARNINGS: INCLUDE_SMHI_WEATHER_WARNINGS_DEFAULT,
    CONF_NEWS_DAYS: NEWS_DEFAULT_DAYS,
    CONF_MAX_ITEMS: MAX_ITEMS_DEFAULT,
    CONF_INCLUDE_NATIONAL: INCLUDE_NATIONAL_DEFAULT,
    CONF_INCLUDE_UNLOCATED: INCLUDE_UNLOCATED_DEFAULT,
}


def _option_value(entry: ConfigEntry, key: str) -> Any:
    """Read options while supporting values stored by older releases."""
    if key in entry.options:
        return entry.options[key]
    return entry.data.get(key, _OPTION_DEFAULTS[key])


def _options_schema(defaults: dict[str, Any]) -> dict[vol.Marker, Any]:
    """Return the shared source and filter options schema."""
    return {
        vol.Optional(CONF_LANGUAGE, default=defaults[CONF_LANGUAGE]): vol.In(
            ["sv-SE", "en-US"]
        ),
        vol.Optional(
            CONF_INCLUDE_UPDATE_CANCEL,
            default=defaults[CONF_INCLUDE_UPDATE_CANCEL],
        ): bool,
        vol.Optional(CONF_SEVERITY_MIN, default=defaults[CONF_SEVERITY_MIN]): vol.In(
            ["Minor", "Moderate", "Severe", "Extreme"]
        ),
        vol.Optional(CONF_API_ENV, default=defaults[CONF_API_ENV]): vol.In(
            [API_ENV_PRODUCTION, API_ENV_TEST]
        ),
        vol.Optional(CONF_INCLUDE_NEWS, default=defaults[CONF_INCLUDE_NEWS]): bool,
        vol.Optional(
            CONF_INCLUDE_NOTICES, default=defaults[CONF_INCLUDE_NOTICES]
        ): bool,
        vol.Optional(
            CONF_INCLUDE_SMHI_WEATHER_WARNINGS,
            default=defaults[CONF_INCLUDE_SMHI_WEATHER_WARNINGS],
        ): bool,
        vol.Optional(CONF_NEWS_DAYS, default=defaults[CONF_NEWS_DAYS]): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=30)
        ),
        vol.Optional(CONF_MAX_ITEMS, default=defaults[CONF_MAX_ITEMS]): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=50)
        ),
        vol.Optional(
            CONF_INCLUDE_NATIONAL, default=defaults[CONF_INCLUDE_NATIONAL]
        ): bool,
        vol.Optional(
            CONF_INCLUDE_UNLOCATED, default=defaults[CONF_INCLUDE_UNLOCATED]
        ): bool,
    }


DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default="Krisinformation"): str,
        vol.Required(CONF_MUNICIPALITY, default=MUNICIPALITY_DEFAULT): vol.In(
            MUNICIPALITY_OPTIONS
        ),
        **_options_schema(_OPTION_DEFAULTS),
    }
)


def _split_input(user_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split connection identity from optional behavior settings."""
    data = {
        CONF_NAME: user_input.get(CONF_NAME, "Krisinformation"),
        CONF_MUNICIPALITY: user_input[CONF_MUNICIPALITY],
    }
    options = {
        key: user_input.get(key, default) for key, default in _OPTION_DEFAULTS.items()
    }
    return data, options


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle source and filter options."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {
            key: _option_value(self.config_entry, key) for key in _OPTION_DEFAULTS
        }
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(_options_schema(defaults))
        )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Krisinformation."""

    VERSION = 5

    def __init__(self) -> None:
        self._pending_entry_title: str | None = None
        self._pending_entry_data: dict[str, Any] | None = None
        self._pending_entry_options: dict[str, Any] | None = None

    def _show_reload_notice_step(
        self, *, title: str, data: dict[str, Any], options: dict[str, Any]
    ):
        """Store entry payload and show final reload notice step."""
        self._pending_entry_title = title
        self._pending_entry_data = data
        self._pending_entry_options = options
        return self.async_show_form(step_id="reload_notice", data_schema=vol.Schema({}))

    async def async_step_reload_notice(self, user_input=None):
        """Show the final confirmation step before creating an entry."""
        if user_input is None:
            return self.async_show_form(
                step_id="reload_notice", data_schema=vol.Schema({})
            )

        if (
            self._pending_entry_title is None
            or self._pending_entry_data is None
            or self._pending_entry_options is None
        ):
            return self.async_abort(reason="reconfigure_entry_missing")

        title = self._pending_entry_title
        data = self._pending_entry_data
        options = self._pending_entry_options
        self._pending_entry_title = None
        self._pending_entry_data = None
        self._pending_entry_options = None
        return self.async_create_entry(title=title, data=data, options=options)

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            data, options = _split_input(user_input)
            title = f"{data[CONF_NAME]} ({data[CONF_MUNICIPALITY]})"
            return self._show_reload_notice_step(
                title=title, data=data, options=options
            )

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

    async def async_step_reconfigure(self, user_input=None):
        entry = getattr(self, "reconfigure_entry", None)
        if entry is None:
            entry_id = self.context.get("entry_id")
            if entry_id:
                entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            return self.async_abort(reason="reconfigure_entry_missing")

        defaults = {key: _option_value(entry, key) for key in _OPTION_DEFAULTS}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=entry.data.get(CONF_NAME, "Krisinformation")
                ): str,
                vol.Required(
                    CONF_MUNICIPALITY,
                    default=entry.data.get(CONF_MUNICIPALITY, MUNICIPALITY_DEFAULT),
                ): vol.In(MUNICIPALITY_OPTIONS),
                **_options_schema(defaults),
            }
        )

        if user_input is not None:
            new_data, new_options = _split_input(user_input)
            return self.async_update_reload_and_abort(
                entry,
                data=new_data,
                options={**entry.options, **new_options},
                reason="reconfigured",
            )

        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()
