import logging
from typing import Any, Dict, List

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_NAME,
    CONF_INCLUDE_NEWS,
    CONF_INCLUDE_NOTICES,
    CONF_MUNICIPALITY,
    CONTENT_DEVICE_MANUFACTURER,
    CONTENT_DEVICE_MODEL,
    DEVICE_MANUFACTURER,
    DEVICE_MODEL,
    INCLUDE_NEWS_DEFAULT,
    INCLUDE_NOTICES_DEFAULT,
)
from .helpers import (
    content_device_identifier,
    legacy_location_slug,
    news_unique_id,
    notices_unique_id,
    vma_count_unique_id,
    vma_device_identifier,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    runtime_data = config_entry.runtime_data
    entities: list[SensorEntity] = [
        KrisinformationCountSensor(config_entry.entry_id, runtime_data.vma_coordinator)
    ]
    if config_entry.options.get(
        CONF_INCLUDE_NEWS,
        config_entry.data.get(CONF_INCLUDE_NEWS, INCLUDE_NEWS_DEFAULT),
    ):
        entities.append(
            KrisinformationNewsSensor(config_entry, runtime_data.news_coordinator)
        )
    if config_entry.options.get(
        CONF_INCLUDE_NOTICES,
        config_entry.data.get(CONF_INCLUDE_NOTICES, INCLUDE_NOTICES_DEFAULT),
    ):
        entities.append(
            KrisinformationNoticesSensor(config_entry, runtime_data.notices_coordinator)
        )
    async_add_entities(entities)


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


class _BaseContentSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for Krisinformation content collections."""

    _attr_has_entity_name = True
    _attr_attribution = "Data from Krisinformation.se"
    _unrecorded_attributes = frozenset({"items", "latest"})

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(coordinator)
        self._entry_id = entry.entry_id
        self._location = entry.data.get(CONF_MUNICIPALITY, "Hela Sverige")

    @property
    def device_info(self):
        return {
            "identifiers": {content_device_identifier(self._entry_id)},
            "manufacturer": CONTENT_DEVICE_MANUFACTURER,
            "model": CONTENT_DEVICE_MODEL,
            "name": f"Krisinformation ({self._location})",
            "configuration_url": "https://www.krisinformation.se",
        }

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data or ())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = [item.as_dict() for item in (self.coordinator.data or ())]
        return {"items": items, "latest": items[0] if items else None}


class KrisinformationNewsSensor(_BaseContentSensor):
    """Expose filtered Krisinformation news."""

    _attr_translation_key = "news"
    _attr_icon = "mdi:newspaper-variant-outline"

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = news_unique_id(entry.entry_id)


class KrisinformationNoticesSensor(_BaseContentSensor):
    """Expose filtered Krisinformation notices."""

    _attr_translation_key = "notices"
    _attr_icon = "mdi:message-alert-outline"

    def __init__(self, entry: ConfigEntry, coordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = notices_unique_id(entry.entry_id)
