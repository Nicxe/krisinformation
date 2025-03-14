from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_NAME, CONF_COUNTY

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KrisinformationSensor(coordinator)], True)

class KrisinformationSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = coordinator.config.get(CONF_NAME, "Krisinformation varningar")
        county = coordinator.config.get(CONF_COUNTY)
        self._attr_unique_id = f"krisinformation_sensor_{county.lower().replace(' ', '_')}"
        self._county = county

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
        for alert in filtered_alerts:
            # Hämta och rensa Headline från avslutande kolon
            headline = alert.get("Headline", "")
            if headline.endswith(":"):
                headline = headline[:-1].strip()
            area_info = self._get_area_info(alert)
            summary = {
                "Headline": headline,
                "PushMessage": alert.get("PushMessage"),
                "Published": alert.get("Published"),
                "Area": area_info
            }
            summary_list.append(summary)
        return {"alerts": summary_list}

    def _filter_alerts(self, data):
        filtered = []
        if data:
            if isinstance(data, list):
                for alert in data:
                    if self._alert_matches_county(alert):
                        filtered.append(alert)
            elif isinstance(data, dict):
                for alert in data.get("alerts", []):
                    if self._alert_matches_county(alert):
                        filtered.append(alert)
        return filtered

    def _alert_matches_county(self, alert):
        if self._county.lower() == "hela sverige":
            return True
        areas = alert.get("Area", [])
        for area in areas:
            if area.get("Type", "").lower() == "county" and area.get("Description", "").lower() == self._county.lower():
                return True
        return False

    def _get_area_info(self, alert):
        areas = alert.get("Area", [])
        for area in areas:
            if area.get("Type", "").lower() == "county":
                return {
                    "Description": area.get("Description")
                }
        return {}