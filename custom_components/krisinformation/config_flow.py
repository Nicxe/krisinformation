import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_MUNICIPALITY,
    MUNICIPALITY_DEFAULT,
    MUNICIPALITY_OPTIONS,
    CONF_LANGUAGE,
    LANGUAGE_DEFAULT,
    CONF_INCLUDE_UPDATE_CANCEL,
    INCLUDE_UPDATE_CANCEL_DEFAULT,
    CONF_SEVERITY_MIN,
    SEVERITY_MIN_DEFAULT,
    CONF_API_ENV,
    API_ENV_PRODUCTION,
    API_ENV_TEST,
)


DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default="Krisinformation"): str,
        vol.Required(CONF_MUNICIPALITY, default=MUNICIPALITY_DEFAULT): vol.In(
            MUNICIPALITY_OPTIONS
        ),
        vol.Optional(CONF_LANGUAGE, default=LANGUAGE_DEFAULT): vol.In(
            ["sv-SE", "en-US"]
        ),
        vol.Optional(
            CONF_INCLUDE_UPDATE_CANCEL, default=INCLUDE_UPDATE_CANCEL_DEFAULT
        ): bool,
        vol.Optional(CONF_SEVERITY_MIN, default=SEVERITY_MIN_DEFAULT): vol.In(
            ["Minor", "Moderate", "Severe", "Extreme"]
        ),
        vol.Optional(CONF_API_ENV, default=API_ENV_PRODUCTION): vol.In(
            [API_ENV_PRODUCTION, API_ENV_TEST]
        ),
    }
)


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_LANGUAGE, default=options.get(CONF_LANGUAGE, LANGUAGE_DEFAULT)
                ): vol.In(["sv-SE", "en-US"]),
                vol.Optional(
                    CONF_INCLUDE_UPDATE_CANCEL,
                    default=options.get(
                        CONF_INCLUDE_UPDATE_CANCEL, INCLUDE_UPDATE_CANCEL_DEFAULT
                    ),
                ): bool,
                vol.Optional(
                    CONF_SEVERITY_MIN,
                    default=options.get(CONF_SEVERITY_MIN, SEVERITY_MIN_DEFAULT),
                ): vol.In(["Minor", "Moderate", "Severe", "Extreme"]),
                vol.Optional(
                    CONF_API_ENV,
                    default=options.get(CONF_API_ENV, API_ENV_PRODUCTION),
                ): vol.In([API_ENV_PRODUCTION, API_ENV_TEST]),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    def __init__(self) -> None:
        self._pending_entry_title: str | None = None
        self._pending_entry_data: dict | None = None

    def _show_reload_notice_step(self, *, title: str, data: dict):
        """Store entry payload and show final reload notice step."""
        self._pending_entry_title = title
        self._pending_entry_data = data
        return self.async_show_form(step_id="reload_notice", data_schema=vol.Schema({}))

    async def async_step_reload_notice(self, user_input=None):
        """Final confirmation step before creating entry."""
        if user_input is None:
            return self.async_show_form(
                step_id="reload_notice", data_schema=vol.Schema({})
            )

        if self._pending_entry_title is None or self._pending_entry_data is None:
            return self.async_abort(reason="reconfigure_entry_missing")

        title = self._pending_entry_title
        data = self._pending_entry_data
        self._pending_entry_title = None
        self._pending_entry_data = None
        return self.async_create_entry(title=title, data=data)

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            municipality = user_input[CONF_MUNICIPALITY]
            base_name = user_input.get(CONF_NAME, "Krisinformation")
            title = f"{base_name} ({municipality})"
            # Store all chosen values in data at creation time
            data = {
                CONF_NAME: base_name,
                CONF_MUNICIPALITY: municipality,
                CONF_LANGUAGE: user_input.get(CONF_LANGUAGE, LANGUAGE_DEFAULT),
                CONF_INCLUDE_UPDATE_CANCEL: user_input.get(
                    CONF_INCLUDE_UPDATE_CANCEL, INCLUDE_UPDATE_CANCEL_DEFAULT
                ),
                CONF_SEVERITY_MIN: user_input.get(
                    CONF_SEVERITY_MIN, SEVERITY_MIN_DEFAULT
                ),
                CONF_API_ENV: user_input.get(CONF_API_ENV, API_ENV_PRODUCTION),
            }
            return self._show_reload_notice_step(title=title, data=data)

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

    async def async_step_reconfigure(self, user_input=None):
        entry = getattr(self, "reconfigure_entry", None)
        if entry is None:
            # Fallback to context-provided entry_id (HA sets this in reconfigure flows)
            entry_id = self.context.get("entry_id")
            if entry_id:
                entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            return self.async_abort(reason="reconfigure_entry_missing")

        data_defaults = {
            CONF_NAME: entry.data.get(CONF_NAME, "Krisinformation"),
            CONF_MUNICIPALITY: entry.data.get(CONF_MUNICIPALITY, MUNICIPALITY_DEFAULT),
        }
        opt_defaults = {
            CONF_LANGUAGE: entry.options.get(CONF_LANGUAGE, LANGUAGE_DEFAULT),
            CONF_INCLUDE_UPDATE_CANCEL: entry.options.get(
                CONF_INCLUDE_UPDATE_CANCEL, INCLUDE_UPDATE_CANCEL_DEFAULT
            ),
            CONF_SEVERITY_MIN: entry.options.get(
                CONF_SEVERITY_MIN, SEVERITY_MIN_DEFAULT
            ),
            CONF_API_ENV: entry.options.get(CONF_API_ENV, API_ENV_PRODUCTION),
        }

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=data_defaults[CONF_NAME]): str,
                vol.Required(
                    CONF_MUNICIPALITY, default=data_defaults[CONF_MUNICIPALITY]
                ): vol.In(MUNICIPALITY_OPTIONS),
                vol.Optional(
                    CONF_LANGUAGE, default=opt_defaults[CONF_LANGUAGE]
                ): vol.In(["sv-SE", "en-US"]),
                vol.Optional(
                    CONF_INCLUDE_UPDATE_CANCEL,
                    default=opt_defaults[CONF_INCLUDE_UPDATE_CANCEL],
                ): bool,
                vol.Optional(
                    CONF_SEVERITY_MIN, default=opt_defaults[CONF_SEVERITY_MIN]
                ): vol.In(["Minor", "Moderate", "Severe", "Extreme"]),
                vol.Optional(CONF_API_ENV, default=opt_defaults[CONF_API_ENV]): vol.In(
                    [API_ENV_PRODUCTION, API_ENV_TEST]
                ),
            }
        )

        if user_input is not None:
            new_data = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_MUNICIPALITY: user_input[CONF_MUNICIPALITY],
            }
            new_options = {
                CONF_LANGUAGE: user_input.get(
                    CONF_LANGUAGE, opt_defaults[CONF_LANGUAGE]
                ),
                CONF_INCLUDE_UPDATE_CANCEL: user_input.get(
                    CONF_INCLUDE_UPDATE_CANCEL, opt_defaults[CONF_INCLUDE_UPDATE_CANCEL]
                ),
                CONF_SEVERITY_MIN: user_input.get(
                    CONF_SEVERITY_MIN, opt_defaults[CONF_SEVERITY_MIN]
                ),
                CONF_API_ENV: user_input.get(CONF_API_ENV, opt_defaults[CONF_API_ENV]),
            }

            return self.async_update_reload_and_abort(
                entry, data=new_data, options=new_options, reason="reconfigured"
            )

        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()
