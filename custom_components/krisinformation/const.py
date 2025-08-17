"""Constants for the Krisinformation integration."""

from __future__ import annotations

DOMAIN = "krisinformation"

# Config/Options keys
CONF_NAME = "name"
CONF_MUNICIPALITY = "municipality"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_LANGUAGE = "language"
CONF_INCLUDE_RESOURCES = "include_resources"
CONF_ACTIVE_ONLY = "active_only"
CONF_INCLUDE_UPDATE_CANCEL = "include_update_cancel"
CONF_SEVERITY_MIN = "severity_min"
CONF_URGENCY = "urgency"
CONF_CERTAINTY = "certainty"
CONF_AREAS = "areas"  # comma-separated list of municipalities/counties
CONF_API_ENV = "api_environment"  # 'production' | 'test'

# Defaults
MUNICIPALITY_DEFAULT = "Hela Sverige"
LANGUAGE_DEFAULT = "sv-SE"
UPDATE_INTERVAL_DEFAULT_SECONDS = 300
INCLUDE_RESOURCES_DEFAULT = True
ACTIVE_ONLY_DEFAULT = True
INCLUDE_UPDATE_CANCEL_DEFAULT = False
SEVERITY_MIN_DEFAULT = "Minor"  # Minor, Moderate, Severe, Extreme
API_ENV_PRODUCTION = "production"
API_ENV_TEST = "test"

# API endpoints for fetching alerts
# Reference: `https://vmaapi.sr.se/index.html`
PRODUCTION_BASE_URL = "https://vmaapi.sr.se/api/v3/alerts"
TEST_BASE_URL = "https://vmaapi.sr.se/testapi/v3/alerts"

# HTTP
DEFAULT_TIMEOUT_SECONDS = 10
USER_AGENT = "HomeAssistant-Krisinformation/1.1 (+https://www.home-assistant.io/)"

# Events
EVENT_NEW_ALERT = f"{DOMAIN}_new_alert"
EVENT_UPDATED_ALERT = f"{DOMAIN}_updated_alert"
EVENT_CANCELED_ALERT = f"{DOMAIN}_canceled_alert"

# Device info
DEVICE_MANUFACTURER = "Sveriges Radio / MSB"
DEVICE_MODEL = "VMA v3 API"

# Severity ordering for filtering/aggregation
SEVERITY_ORDER = ["Minor", "Moderate", "Severe", "Extreme"]

from .municipalities import (
    COUNTY_MAPPING,
    MUNICIPALITY_MAPPING,
    MUNICIPALITY_OPTIONS,
)

