import logging
from typing import Any, Dict, List
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NAME,
    CONF_MUNICIPALITY,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
)
from .helpers import legacy_location_slug, vma_count_unique_id, vma_device_identifier

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator = config_entry.runtime_data.vma_coordinator
    async_add_entities(
        [
            KrisinformationCountSensor(config_entry.entry_id, coordinator),
        ],
    )


class _BaseKrisinformationEntity(CoordinatorEntity, SensorEntity):
    _unrecorded_attributes = frozenset({"alerts"})

    def __init__(self, entry_id: str, coordinator) -> None:
        super().__init__(coordinator)
        config = coordinator.config
        municipality = config.get(CONF_MUNICIPALITY, "Hela Sverige")
        base_name = config.get(CONF_NAME, "Krisinformation")

        sanitized = legacy_location_slug(municipality)
        self._entry_id = entry_id
        self._municipality = municipality
        self._base_name = base_name
        self._sanitized = sanitized

    @property
    def device_info(self):
        return {
            "identifiers": {vma_device_identifier(self._entry_id)},
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
        return vma_count_unique_id(self._entry_id)

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
