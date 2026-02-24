"""Constants for the Krisinformation integration."""

from __future__ import annotations

import json
from importlib import resources

from .municipalities import COUNTY_MAPPING, MUNICIPALITY_MAPPING, MUNICIPALITY_OPTIONS

DOMAIN = "krisinformation"

# Frontend card resource handling
CARD_FILENAME = "krisinformation-alert-card.js"
CARD_WWW_DIR = "www"
CARD_STATIC_BASE_PATH = f"/{DOMAIN}-static"
CARD_CANONICAL_BASE_URL = f"{CARD_STATIC_BASE_PATH}/{CARD_FILENAME}"
CARD_LEGACY_BASE_URL = f"/local/{CARD_FILENAME}"
FRONTEND_DATA_KEY = f"{DOMAIN}_frontend"
FRONTEND_DATA_COMPONENT_LISTENER = f"{DOMAIN}_component_listener"

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
USER_AGENT_PRODUCT = "HomeAssistantKrisinformation"


def _load_manifest_version() -> str:
    """Return the integration version defined in manifest.json."""
    try:
        manifest_path = resources.files(__package__).joinpath("manifest.json")
        manifest_raw = manifest_path.read_text(encoding="utf-8")
        manifest = json.loads(manifest_raw)
    except (FileNotFoundError, json.JSONDecodeError, AttributeError, OSError):
        return "0.0.0"
    return manifest.get("version", "0.0.0")


INTEGRATION_VERSION = _load_manifest_version()

# Events
EVENT_NEW_ALERT = f"{DOMAIN}_new_alert"
EVENT_UPDATED_ALERT = f"{DOMAIN}_updated_alert"
EVENT_CANCELED_ALERT = f"{DOMAIN}_canceled_alert"

# Device info
DEVICE_MANUFACTURER = "Sveriges Radio / MSB"
DEVICE_MODEL = "VMA v3 API"

# Severity ordering for filtering/aggregation
SEVERITY_ORDER = ["Minor", "Moderate", "Severe", "Extreme"]

__all__ = [
    "COUNTY_MAPPING",
    "MUNICIPALITY_MAPPING",
    "MUNICIPALITY_OPTIONS",
]
