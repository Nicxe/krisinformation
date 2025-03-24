import asyncio
import logging
from datetime import timedelta
import async_timeout
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DOMAIN,
    CONF_MUNICIPALITY,
    MUNICIPALITY_DEFAULT,
    COUNTY_MAPPING,
    MUNICIPALITY_MAPPING,
)

_LOGGER = logging.getLogger(__name__)
DEFAULT_UPDATE_INTERVAL = 300  # 5 minuter

def _get_geocode(selected):
    if not selected or selected == "Hela Sverige":
        return ""
    if selected.endswith("län"):
        return COUNTY_MAPPING.get(selected, "")
    return MUNICIPALITY_MAPPING.get(selected, "")


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    session = aiohttp.ClientSession()
    coordinator = KrisinformationDataUpdateCoordinator(
        hass, session, entry.data, timedelta(seconds=DEFAULT_UPDATE_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class KrisinformationDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, config, update_interval):
        super().__init__(hass, _LOGGER, name="Krisinformation Data Update Coordinator", update_interval=update_interval)
        self.session = session
        self.config = config

    async def _async_update_data(self):
        base_url = "https://vmaapi.sr.se/api/v3-beta/alerts"
        selected = self.config.get(CONF_MUNICIPALITY, MUNICIPALITY_DEFAULT)
        geocode = _get_geocode(selected)
        url = base_url
        if geocode:
            url += f"?geocode={geocode}"

        try:
            async with async_timeout.timeout(10):
                async with self.session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data
        except Exception as e:
            _LOGGER.error("Fel vid hämtning från UR:s API: %s", e)
            return {}