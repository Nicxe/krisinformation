"""Constants for the Krisinformation integration."""

DOMAIN = "krisinformation"

CONF_NAME = "name"
CONF_MUNICIPALITY = "municipality"

MUNICIPALITY_DEFAULT = "Hela Sverige"

# API endpoint for fetching alerts
BASE_URL = "https://vmaapi.sr.se/api/v3-beta/alerts"

from .municipalities import (
    COUNTY_MAPPING,
    MUNICIPALITY_MAPPING,
    MUNICIPALITY_OPTIONS,
)

