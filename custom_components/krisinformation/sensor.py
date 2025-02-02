from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_NAME, CONF_COUNTY

async def async_setup_entry(hass, entry, async_add_entities):
    """Ställ in sensorn via config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KrisinformationSensor(coordinator)], True)

class KrisinformationSensor(CoordinatorEntity, SensorEntity):
    """Sensor för Krisinformation-varningar filtrerat på län baserat på Area/Description."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = coordinator.config.get(CONF_NAME, "Krisinformation varningar")
        county = coordinator.config.get(CONF_COUNTY)
        # Generera unikt ID baserat på valt län (ersätt mellanslag med understreck)
        self._attr_unique_id = f"krisinformation_sensor_{county.lower().replace(' ', '_')}"
        self._county = county

    @property
    def state(self):
        """Returnera antalet varningar för det angivna länet (eller hela Sverige)."""
        data = self.coordinator.data
        filtered_alerts = self._filter_alerts(data)
        return len(filtered_alerts)

    @property
    def extra_state_attributes(self):
        """Returnera en sammanfattning av varningarna med utvalda fält."""
        data = self.coordinator.data
        filtered_alerts = self._filter_alerts(data)
        summary_list = []
        for alert in filtered_alerts:
            summary = {
                "Identifier": alert.get("Identifier"),
                "Headline": alert.get("Headline"),
                "PushMessage": alert.get("PushMessage"),
                "Published": alert.get("Published"),
                "Preamble": alert.get("Preamble"),
                "Area": self._get_area_info(alert)
            }
            summary_list.append(summary)
        return {"alerts": summary_list}

    def _filter_alerts(self, data):
        """Filtrera ut varningar baserat på county i Area/Description.
           Om 'Hela Sverige' är valt, returnera alla varningar."""
        if not data:
            return []
        # Om användaren vill se alla varningar
        if self._county.lower() == "hela sverige":
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("alerts", [])
            else:
                return []
        # Annars filtrera baserat på valt län
        filtered = []
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
        """Returnera True om någon Area-post med Type 'County' matchar det angivna länet."""
        areas = alert.get("Area", [])
        for area in areas:
            if area.get("Type", "").lower() == "county" and area.get("Description", "").lower() == self._county.lower():
                return True
        return False

    def _get_area_info(self, alert):
        """Returnera area-information för county från alerten med Description och Coordinates."""
        areas = alert.get("Area", [])
        for area in areas:
            if area.get("Type", "").lower() == "county":
                return {
                    "Description": area.get("Description"),
                    "Coordinates": area.get("GeometryInformation", {}).get("PoleOfInInaccessibility", {}).get("coordinates")
                }
        return {}