import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_MUNICIPALITY,
    MUNICIPALITY_DEFAULT,
    MUNICIPALITY_OPTIONS,
)

DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default="Krisinformation"): str,
    vol.Required(CONF_MUNICIPALITY, default=MUNICIPALITY_DEFAULT): vol.In(MUNICIPALITY_OPTIONS),
})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            municipality = user_input[CONF_MUNICIPALITY]
            base_name = user_input.get(CONF_NAME, "Krisinformation")

            title = f"{base_name} ({municipality})"
            return self.async_create_entry(
                title=title,
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA
        )
