import logging
from typing import Any, Dict, List
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_MUNICIPALITY,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            KrisinformationCountSensor(config_entry.entry_id, coordinator),
        ],
    )


class _BaseKrisinformationEntity(CoordinatorEntity, SensorEntity):
    def __init__(self, entry_id: str, coordinator) -> None:
        super().__init__(coordinator)
        config = coordinator.config
        municipality = config.get(CONF_MUNICIPALITY, "Hela Sverige")
        base_name = config.get(CONF_NAME, "Krisinformation")

        sanitized = (
            municipality.lower()
            .replace(" ", "_")
            .replace("å", "a")
            .replace("ä", "a")
            .replace("ö", "o")
            .replace("é", "e")
        )
        self._entry_id = entry_id
        self._municipality = municipality
        self._base_name = base_name
        self._sanitized = sanitized

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._sanitized}_{self._entry_id}")},
            "manufacturer": DEVICE_MANUFACTURER,
            "model": DEVICE_MODEL,
            "name": f"Krisinformation ({self._municipality})",
        }


class KrisinformationCountSensor(_BaseKrisinformationEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self) -> str:
        return f"{self._base_name} ({self._municipality})"

    @property
    def unique_id(self) -> str:
        # Keep legacy unique_id so existing entity_id is preserved
        return f"krisinformation_sensor_{self._sanitized}_{self._entry_id}"

    @property
    def state(self) -> int:
        data = self.coordinator.data or {}
        alerts: List[Dict[str, Any]] = data.get("alerts") or []
        return len(alerts)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        alerts: List[Dict[str, Any]] = data.get("alerts") or []
        # Expose full CAP list for dashboards/automation templates
        return {"alerts": alerts}

    # Note: The former list sensor has been merged into this count sensor.
