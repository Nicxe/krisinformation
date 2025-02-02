import logging
from datetime import timedelta
import async_timeout

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
DEFAULT_UPDATE_INTERVAL = 300  # Uppdateras var 5:e minut

async def async_setup(hass, config):
    """Setup via YAML (inget behövs då vi använder config flow)."""
    return True

async def async_setup_entry(hass, entry):
    """Initiera integrationen via config entry."""
    session = async_get_clientsession(hass)

    coordinator = KrisinformationDataUpdateCoordinator(
        hass, session, entry.data, timedelta(seconds=DEFAULT_UPDATE_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Vidarebefordra plattformar asynkront
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass, entry):
    """Avlasta integrationen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class KrisinformationDataUpdateCoordinator(DataUpdateCoordinator):
    """Koordinator för att hämta data från Krisinformation API."""
    def __init__(self, hass, session, config, update_interval):
        super().__init__(hass, _LOGGER, name="Krisinformation", update_interval=update_interval)
        self.session = session
        self.config = config

    async def _async_update_data(self):
        """Hämta data från Krisinformation API."""
        url = "https://api.krisinformation.se/v3/vmas"
        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(url)
                response.raise_for_status()
                data = await response.json()
                return data
        except Exception as e:
            _LOGGER.error("Fel vid hämtning från Krisinformation API: %s", e)
            return {}