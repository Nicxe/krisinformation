import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import async_timeout
import re
from aiohttp import ClientError, ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import KrisinformationApiClient, integration_user_agent
from .const import (
    ACTIVE_ONLY_DEFAULT,
    API_ENV_PRODUCTION,
    API_ENV_TEST,
    CONF_ACTIVE_ONLY,
    CONF_API_ENV,
    CONF_INCLUDE_UPDATE_CANCEL,
    CONF_LANGUAGE,
    CONF_MUNICIPALITY,
    CONF_SEVERITY_MIN,
    CONF_UPDATE_INTERVAL,
    COUNTY_MAPPING,
    DEFAULT_TIMEOUT_SECONDS,
    DOMAIN,
    EVENT_CANCELED_ALERT,
    EVENT_NEW_ALERT,
    EVENT_UPDATED_ALERT,
    INCLUDE_UPDATE_CANCEL_DEFAULT,
    LANGUAGE_DEFAULT,
    MUNICIPALITY_DEFAULT,
    MUNICIPALITY_MAPPING,
    PRODUCTION_BASE_URL,
    SEVERITY_MIN_DEFAULT,
    SEVERITY_ORDER,
    TEST_BASE_URL,
    UPDATE_INTERVAL_DEFAULT_SECONDS,
    VMA_MAX_BACKOFF_SECONDS,
    VMA_PRODUCTION_STATUSES,
    VMA_TEST_STATUSES,
    VMA_UPDATE_INTERVAL_SECONDS,
)
from .coordinator import (
    KrisinformationNewsCoordinator,
    KrisinformationNoticesCoordinator,
)
from .frontend import async_setup_frontend
from .helpers import (
    legacy_location_slug,
    vma_active_unique_id,
    vma_count_unique_id,
    vma_device_identifier,
)
from .runtime_data import KrisinformationRuntimeData

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_RE_WHITESPACE = re.compile(r"\s+")


def _sanitize_text(value: Optional[str]) -> Optional[str]:
    """Normalize text from SR VMA API (CRLF/newlines/odd whitespace)."""
    if value is None:
        return None
    if not isinstance(value, str):
        # Defensive: keep non-string as-is rather than crashing
        return value  # type: ignore[return-value]

    # Normalize newlines: CRLF/CR -> LF
    text = value.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize any whitespace (spaces, tabs, newlines) into a single space
    # This avoids odd-looking multiline rendering in HA attributes.
    text = _RE_WHITESPACE.sub(" ", text)
    return text.strip()


def _get_geocode(selected: Optional[str]) -> str:
    if not selected or selected == "Hela Sverige":
        return ""
    if selected.endswith("län"):
        return COUNTY_MAPPING.get(selected, "")
    return MUNICIPALITY_MAPPING.get(selected, "")


async def async_setup(hass, config):
    await async_setup_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    await _async_migrate_registry_identifiers(hass, entry)
    session = async_get_clientsession(hass)
    coordinator = KrisinformationDataUpdateCoordinator(
        hass, session, entry, timedelta(seconds=VMA_UPDATE_INTERVAL_SECONDS)
    )
    await coordinator.async_config_entry_first_refresh()
    api_client = KrisinformationApiClient(session)
    entry.runtime_data = KrisinformationRuntimeData(
        vma_coordinator=coordinator,
        api_client=api_client,
        news_coordinator=KrisinformationNewsCoordinator(hass, api_client, entry),
        notices_coordinator=KrisinformationNoticesCoordinator(hass, api_client, entry),
    )

    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor"]
    )

    async def _options_update_listener(hass: HomeAssistant, updated_entry: ConfigEntry):
        await hass.config_entries.async_reload(updated_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_options_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, ["sensor", "binary_sensor"]
    )
    if unload_ok:
        entry.runtime_data = None
    return unload_ok


async def _async_migrate_registry_identifiers(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Migrate location-dependent entity and device identifiers."""
    municipality = entry.data.get(CONF_MUNICIPALITY, MUNICIPALITY_DEFAULT)
    legacy_slug = legacy_location_slug(municipality)
    legacy_unique_ids = {
        f"krisinformation_sensor_{legacy_slug}_{entry.entry_id}": vma_count_unique_id(
            entry.entry_id
        ),
        f"krisinformation_active_{legacy_slug}_{entry.entry_id}": vma_active_unique_id(
            entry.entry_id
        ),
    }

    @callback
    def _migrate_entity(entity_entry: er.RegistryEntry) -> dict[str, str] | None:
        if new_unique_id := legacy_unique_ids.get(entity_entry.unique_id):
            return {"new_unique_id": new_unique_id}
        return None

    await er.async_migrate_entries(hass, entry.entry_id, _migrate_entity)

    device_registry = dr.async_get(hass)
    legacy_identifier = (DOMAIN, f"{legacy_slug}_{entry.entry_id}")
    if device := device_registry.async_get_device(identifiers={legacy_identifier}):
        device_registry.async_update_device(
            device.id,
            new_identifiers=(device.identifiers - {legacy_identifier})
            | {vma_device_identifier(entry.entry_id)},
        )


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry to the latest version."""
    if entry.version == 1:
        _LOGGER.debug("Migrating config entry from v1 to v2 for %s", entry.title)

        # Keep existing data as-is (name, municipality)
        new_data = {**entry.data}

        # Initialize options with sensible defaults introduced in v2
        new_options = {
            CONF_LANGUAGE: LANGUAGE_DEFAULT,
            CONF_ACTIVE_ONLY: ACTIVE_ONLY_DEFAULT,
            CONF_INCLUDE_UPDATE_CANCEL: INCLUDE_UPDATE_CANCEL_DEFAULT,
            CONF_SEVERITY_MIN: SEVERITY_MIN_DEFAULT,
            CONF_UPDATE_INTERVAL: UPDATE_INTERVAL_DEFAULT_SECONDS,
        }

        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            options=new_options,
            version=2,
        )

        _LOGGER.info("Migration to v2 successful for %s", entry.title)
    if entry.version == 2:
        _LOGGER.debug("Migrating config entry from v2 to v3 for %s", entry.title)
        # Ensure API environment option exists and defaults to production
        new_options = {**entry.options}
        if CONF_API_ENV not in new_options:
            new_options[CONF_API_ENV] = API_ENV_PRODUCTION
        hass.config_entries.async_update_entry(
            entry,
            options=new_options,
            version=3,
        )
        _LOGGER.info("Migration to v3 successful for %s", entry.title)
    return True


class KrisinformationDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, session, config_entry, update_interval):
        super().__init__(
            hass,
            _LOGGER,
            name="Krisinformation Data Update Coordinator",
            update_interval=update_interval,
            config_entry=config_entry,
        )
        self.session = session
        self.config_entry = config_entry
        self.config = config_entry.data
        self.options = config_entry.options

        # State tracking for events
        self._incident_state: Dict[str, Dict[str, Any]] = {}
        self._events_initialized = False

        self._user_agent = self._compose_user_agent()

        # Store default interval for backoff recovery
        self._default_update_interval = update_interval

    def _get_effective_option(self, key: str, default: Any) -> Any:
        # Prefer options; fallback to original data for first-time setup values
        if key in self.options:
            return self.options.get(key)
        return self.config.get(key, default)

    def _get_language(self) -> str:
        return self._get_effective_option(CONF_LANGUAGE, LANGUAGE_DEFAULT)

    def _get_filters(self) -> Dict[str, Any]:
        environment = self._get_effective_option(CONF_API_ENV, API_ENV_PRODUCTION)
        return {
            "active_only": True,  # Always enforce active-only per design
            "include_update_cancel": self._get_effective_option(
                CONF_INCLUDE_UPDATE_CANCEL, INCLUDE_UPDATE_CANCEL_DEFAULT
            ),
            "severity_min": self._get_effective_option(
                CONF_SEVERITY_MIN, SEVERITY_MIN_DEFAULT
            ),
            "statuses": VMA_TEST_STATUSES
            if environment == API_ENV_TEST
            else VMA_PRODUCTION_STATUSES,
        }

    def _compose_url_and_params(self) -> Tuple[str, Dict[str, str]]:
        selected = self.config.get(CONF_MUNICIPALITY, MUNICIPALITY_DEFAULT)
        geocode = _get_geocode(selected)
        # Determine API environment
        env = self._get_effective_option(CONF_API_ENV, API_ENV_PRODUCTION)
        url = TEST_BASE_URL if env == API_ENV_TEST else PRODUCTION_BASE_URL
        params: Dict[str, str] = {}
        if geocode:
            params["geocode"] = geocode
        return url, params

    def _compose_user_agent(self) -> str:
        return integration_user_agent()

    def _build_headers(self) -> Dict[str, str]:
        return {"User-Agent": self._user_agent, "Accept": "application/json"}

    async def _async_update_data(self):
        url, params = self._compose_url_and_params()
        headers = self._build_headers()
        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT_SECONDS):
                async with self.session.get(
                    url, params=params, headers=headers
                ) as response:
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                wait_seconds = int(retry_after)
                            except ValueError:
                                wait_seconds = self.update_interval.total_seconds() * 2
                        else:
                            wait_seconds = self.update_interval.total_seconds() * 2
                        wait_seconds = min(VMA_MAX_BACKOFF_SECONDS, wait_seconds)
                        self.update_interval = timedelta(seconds=wait_seconds)
                        raise UpdateFailed(
                            f"VMA API rate limited requests; retrying in {wait_seconds:g} seconds"
                        )

                    response.raise_for_status()
                    data = await response.json()
        except asyncio.TimeoutError as err:
            raise UpdateFailed(
                f"VMA API request timed out after {DEFAULT_TIMEOUT_SECONDS} seconds"
            ) from err
        except UpdateFailed:
            raise
        except ClientResponseError as err:
            raise UpdateFailed(
                f"VMA API returned HTTP {err.status}: {err.message}"
            ) from err
        except ClientError as err:
            raise UpdateFailed(f"VMA API network error: {err}") from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Unexpected VMA API error: {err}") from err

        if self.update_interval != self._default_update_interval:
            self.update_interval = self._default_update_interval

        # Normalize and filter
        language = self._get_language()
        filters = self._get_filters()
        normalized = self._normalize_data(data, language)
        active_alerts = self._apply_filters(normalized, filters)

        # Events use the complete unfiltered CAP snapshot so sensor preferences do not
        # suppress lifecycle notifications.
        event_alerts = [
            alert for alert in normalized if alert.get("status") in filters["statuses"]
        ]
        self._emit_events(event_alerts)

        return {"alerts": active_alerts}

    def _normalize_data(
        self, raw: Dict[str, Any], language: str
    ) -> List[Dict[str, Any]]:
        alerts = raw.get("alerts") or []
        normalized: List[Dict[str, Any]] = []
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            info_list = alert.get("info") or []
            info_obj = None
            for i in info_list:
                if i and i.get("language") == language:
                    info_obj = i
                    break
            if info_obj is None and info_list:
                info_obj = info_list[0]

            area_list = info_obj.get("area") if info_obj else []
            resources = info_obj.get("resource") if info_obj else []

            normalized.append(
                {
                    "identifier": alert.get("identifier"),
                    "sender": alert.get("sender"),
                    "status": alert.get("status"),
                    "msgType": alert.get("msgType"),
                    "scope": alert.get("scope"),
                    "references": alert.get("references"),
                    "note": alert.get("note"),
                    "incidents": alert.get("incidents"),
                    "sent": alert.get("sent"),
                    "info": {
                        "language": info_obj.get("language") if info_obj else None,
                        "category": info_obj.get("category") if info_obj else None,
                        "event": info_obj.get("event") if info_obj else None,
                        "responseType": info_obj.get("responseType")
                        if info_obj
                        else None,
                        "urgency": info_obj.get("urgency") if info_obj else None,
                        "severity": info_obj.get("severity") if info_obj else None,
                        "certainty": info_obj.get("certainty") if info_obj else None,
                        "effective": info_obj.get("effective") if info_obj else None,
                        "onset": info_obj.get("onset") if info_obj else None,
                        "expires": info_obj.get("expires") if info_obj else None,
                        "headline": _sanitize_text(info_obj.get("headline"))
                        if info_obj
                        else None,
                        "description": _sanitize_text(info_obj.get("description"))
                        if info_obj
                        else None,
                        "instruction": _sanitize_text(info_obj.get("instruction"))
                        if info_obj
                        else None,
                        "contact": info_obj.get("contact") if info_obj else None,
                        "senderName": info_obj.get("senderName") if info_obj else None,
                        "parameters": (info_obj.get("parameters") or [])
                        if info_obj
                        else [],
                        "web": info_obj.get("web") if info_obj else None,
                        "area": area_list or [],
                        "resource": resources or [],
                    },
                }
            )
        return normalized

    def _apply_filters(
        self, alerts: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        active_only: bool = filters.get("active_only", True)
        include_update_cancel: bool = filters.get("include_update_cancel", False)
        severity_min: str = filters.get("severity_min", SEVERITY_MIN_DEFAULT)
        statuses: frozenset[str] = filters.get("statuses", VMA_PRODUCTION_STATUSES)
        min_index = (
            SEVERITY_ORDER.index(severity_min) if severity_min in SEVERITY_ORDER else 0
        )

        def is_active(a: Dict[str, Any]) -> bool:
            info = a.get("info") or {}
            now = dt_util.utcnow()
            try:
                exp = (
                    self._parse_iso(info.get("expires"))
                    if info.get("expires")
                    else None
                )
                eff = (
                    self._parse_iso(info.get("effective"))
                    if info.get("effective")
                    else None
                )
                onset = (
                    self._parse_iso(info.get("onset")) if info.get("onset") else None
                )
            except Exception:  # noqa: BLE001
                exp = eff = onset = None
            start = (
                eff or onset or self._parse_iso(a.get("sent"))
                if a.get("sent")
                else None
            )
            if exp and now >= exp:
                return False
            if start and now < start:
                return False
            return True

        result: List[Dict[str, Any]] = []
        for a in alerts:
            if a.get("status") not in statuses:
                continue
            msg_type = a.get("msgType")
            if not include_update_cancel and msg_type in {"Update", "Cancel"}:
                continue
            info = a.get("info") or {}
            severity = info.get("severity")
            if severity in SEVERITY_ORDER:
                if SEVERITY_ORDER.index(severity) < min_index:
                    continue
            if active_only and not is_active(a):
                continue
            result.append(a)
        return result

    def _parse_iso(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            # Ensure timezone-aware UTC
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _incident_key(alert: Dict[str, Any]) -> str | None:
        """Return a stable lifecycle key for a CAP alert."""
        if incidents := str(alert.get("incidents") or "").split():
            return " ".join(sorted(incidents))

        if references := str(alert.get("references") or "").split():
            referenced_ids = []
            for reference in references:
                parts = reference.split(",")
                referenced_ids.append(parts[1] if len(parts) > 1 else parts[0])
            return " ".join(sorted(referenced_ids))

        identifier = alert.get("identifier")
        return str(identifier) if identifier else None

    def _emit_events(self, current: List[Dict[str, Any]]) -> None:
        """Emit VMA lifecycle events after the initial snapshot is established."""
        current_state = {
            incident_key: alert
            for alert in current
            if (incident_key := self._incident_key(alert))
        }

        if not self._events_initialized:
            self._incident_state = current_state
            self._events_initialized = True
            return

        previous_state = self._incident_state
        for incident_key, alert in current_state.items():
            previous = previous_state.get(incident_key)
            if previous and (
                previous.get("identifier") == alert.get("identifier")
                and previous.get("msgType") == alert.get("msgType")
            ):
                continue

            if alert.get("msgType") == "Alert":
                self.hass.bus.async_fire(EVENT_NEW_ALERT, alert)
            elif alert.get("msgType") == "Update":
                self.hass.bus.async_fire(EVENT_UPDATED_ALERT, alert)
            elif alert.get("msgType") == "Cancel":
                self.hass.bus.async_fire(EVENT_CANCELED_ALERT, alert)

        for incident_key in previous_state.keys() - current_state.keys():
            previous = previous_state[incident_key]
            if previous.get("msgType") == "Cancel":
                continue
            canceled = {
                **previous,
                "msgType": "Cancel",
                "references": previous.get("identifier"),
            }
            self.hass.bus.async_fire(EVENT_CANCELED_ALERT, canceled)

        self._incident_state = current_state
