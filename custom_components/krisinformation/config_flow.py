import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .const import DOMAIN, CONF_COUNTY, COUNTY_OPTIONS

DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default="Krisinformation varningar"): str,
    vol.Required(CONF_COUNTY): vol.In(COUNTY_OPTIONS),
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hantera konfigurationsflödet för Krisinformation-integrationen."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Startsteg för konfigurationsflödet."""
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)