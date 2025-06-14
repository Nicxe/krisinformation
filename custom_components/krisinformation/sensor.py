import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_NAME, CONF_MUNICIPALITY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([KrisinformationSensor(config_entry.entry_id, coordinator)], True)


class KrisinformationSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, entry_id: str, coordinator):
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

        self._attr_name = f"{base_name} ({municipality})"

        self._attr_unique_id = f"krisinformation_sensor_{sanitized}_{entry_id}"

        self._municipality = municipality

    @property
    def state(self):
        data = self.coordinator.data
        filtered_alerts = self._filter_alerts(data)
        return len(filtered_alerts)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        filtered_alerts = self._filter_alerts(data)
        summary_list = []
        for alert, info in filtered_alerts:
            event = info.get("event", "")
            raw_description = info.get("description", "")
            description = " ".join(raw_description.split())
            sent = alert.get("sent", "")
            severity = info.get("severity", "")
            areas_list = [area.get("areaDesc", "") for area in info.get("area", [])]
            areas_str = ", ".join(areas_list) if areas_list else ""
            summary_list.append({
                "identifier": alert.get("identifier", ""),
                "event": event,
                "description": description,
                "sent": sent,
                "severity": severity,
                "areas": areas_str
            })
        return {"alerts": summary_list}

    def _filter_alerts(self, data):
        filtered = []
        if not data or not isinstance(data, dict):
            return filtered

        alerts = data.get("alerts") or []
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            if alert.get("msgType") != "Alert":
                continue

            infos = alert.get("info") or []
            for info in infos:
                if not info:
                    continue
                if info.get("language") != "sv-SE":
                    continue
                filtered.append((alert, info))
                break
        return filtered
