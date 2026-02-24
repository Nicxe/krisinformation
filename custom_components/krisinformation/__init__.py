import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import async_timeout
import re
from aiohttp import ClientError, ClientResponseError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .frontend import async_setup_frontend
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
    INTEGRATION_VERSION,
    LANGUAGE_DEFAULT,
    MUNICIPALITY_DEFAULT,
    MUNICIPALITY_MAPPING,
    PRODUCTION_BASE_URL,
    SEVERITY_MIN_DEFAULT,
    SEVERITY_ORDER,
    TEST_BASE_URL,
    UPDATE_INTERVAL_DEFAULT_SECONDS,
    USER_AGENT_PRODUCT,
)

_LOGGER = logging.getLogger(__name__)
DEFAULT_UPDATE_INTERVAL = 300  # 5 minuter

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
    session = async_get_clientsession(hass)
    coordinator = KrisinformationDataUpdateCoordinator(
        hass, session, entry, timedelta(seconds=DEFAULT_UPDATE_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

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
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


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

        # Caching / conditional requests
        self._etag: Optional[str] = None
        self._last_modified: Optional[str] = None
        self._since_iso: Optional[str] = None

        # State tracking for events
        self._identifier_to_msgtype: Dict[str, str] = {}
        self._last_alert_sent: Optional[str] = None

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
        return {
            "active_only": True,  # Always enforce active-only per design
            "include_update_cancel": self._get_effective_option(
                CONF_INCLUDE_UPDATE_CANCEL, INCLUDE_UPDATE_CANCEL_DEFAULT
            ),
            "severity_min": self._get_effective_option(
                CONF_SEVERITY_MIN, SEVERITY_MIN_DEFAULT
            ),
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
        if self._since_iso:
            params["since"] = self._since_iso
        return url, params

    def _compose_user_agent(self) -> str:
        integration_version = INTEGRATION_VERSION or "0.0.0"
        ha_version = HA_VERSION or "unknown"
        ua = f"{USER_AGENT_PRODUCT}/{integration_version}"
        if ha_version:
            ua = f"{ua} HomeAssistant/{ha_version}"
        return ua

    def _build_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": self._user_agent, "Accept": "application/json"}
        if self._etag:
            headers["If-None-Match"] = self._etag
        if self._last_modified:
            headers["If-Modified-Since"] = self._last_modified
        return headers

    async def _async_update_data(self):
        url, params = self._compose_url_and_params()
        headers = self._build_headers()
        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT_SECONDS):
                async with self.session.get(
                    url, params=params, headers=headers
                ) as response:
                    if response.status == 304:
                        # Not modified: return previous data
                        _LOGGER.debug("304 Not Modified from VMA API")
                        return self.data or {}

                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        _LOGGER.warning(
                            "429 Too Many Requests from VMA API, Retry-After=%s",
                            retry_after,
                        )
                        # Use Retry-After if provided, otherwise exponential backoff
                        if retry_after:
                            try:
                                wait_seconds = int(retry_after)
                            except ValueError:
                                wait_seconds = self.update_interval.total_seconds() * 2
                        else:
                            wait_seconds = self.update_interval.total_seconds() * 2
                        self.update_interval = timedelta(seconds=min(900, wait_seconds))
                        return self.data or {}

                    response.raise_for_status()

                    # Capture caching headers
                    self._etag = response.headers.get("ETag") or self._etag
                    self._last_modified = (
                        response.headers.get("Last-Modified") or self._last_modified
                    )
                    cache_control = response.headers.get("Cache-Control", "")

                    # Adjust polling interval if max-age present
                    if "max-age=" in cache_control:
                        try:
                            max_age = int(
                                cache_control.split("max-age=")[1].split(",")[0]
                            )
                            # Keep sensible bounds
                            self.update_interval = timedelta(
                                seconds=max(60, min(600, max_age))
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    elif self.update_interval > self._default_update_interval:
                        # Gradually recover from backoff after successful request
                        recovered_seconds = max(
                            self._default_update_interval.total_seconds(),
                            self.update_interval.total_seconds() / 2,
                        )
                        self.update_interval = timedelta(seconds=recovered_seconds)
                        _LOGGER.debug(
                            "Recovering from backoff, interval now %s seconds",
                            recovered_seconds,
                        )

                    data = await response.json()
        except asyncio.TimeoutError as err:
            _LOGGER.warning(
                "Timeout vid anrop till VMA API (tidsgräns %ss)",
                DEFAULT_TIMEOUT_SECONDS,
            )
            raise UpdateFailed("API-anrop tog för lång tid") from err
        except ClientResponseError as err:
            _LOGGER.warning(
                "HTTP-fel %s vid anrop till VMA API: %s", err.status, err.message
            )
            raise UpdateFailed(f"HTTP-fel {err.status}: {err.message}") from err
        except ClientError as err:
            _LOGGER.warning("Nätverksfel vid anrop till VMA API: %s", err)
            raise UpdateFailed(f"Nätverksfel: {err}") from err
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Oväntat fel vid anrop till VMA API")
            raise UpdateFailed(f"Oväntat fel: {err}") from err

        # Normalize and filter
        language = self._get_language()
        filters = self._get_filters()
        normalized = self._normalize_data(data, language)
        active_alerts = self._apply_filters(normalized, filters)

        # Emit events comparing with last state (always, regardless of sensor filters)
        self._emit_events(previous=self._identifier_to_msgtype, current=normalized)
        # Update internal map for next diff
        self._identifier_to_msgtype = {
            a["identifier"]: a.get("msgType", "") for a in normalized
        }

        # Advance since cursor using latest sent
        latest_sent = self._extract_latest_sent_iso(normalized)
        if latest_sent and latest_sent != self._last_alert_sent:
            self._since_iso = latest_sent
            self._last_alert_sent = latest_sent

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

    def _extract_latest_sent_iso(self, alerts: List[Dict[str, Any]]) -> Optional[str]:
        latest: Optional[datetime] = None
        latest_str: Optional[str] = None
        for a in alerts:
            s = a.get("sent")
            dt = self._parse_iso(s)
            if dt and (latest is None or dt > latest):
                latest = dt
                latest_str = s
        return latest_str

    def _emit_events(
        self,
        previous: Dict[str, str],
        current: List[Dict[str, Any]],
    ) -> None:
        curr_map = {a["identifier"]: a for a in current if a.get("identifier")}
        prev_ids = set(previous.keys())
        curr_ids = set(curr_map.keys())

        # New
        for new_id in curr_ids - prev_ids:
            alert = curr_map[new_id]
            if alert.get("msgType") == "Alert":
                self.hass.bus.async_fire(EVENT_NEW_ALERT, alert)

        # Updated / Canceled
        for common_id in curr_ids & prev_ids:
            prev_type = previous.get(common_id)
            curr_type = curr_map[common_id].get("msgType")
            if curr_type == "Update" and prev_type != "Update":
                self.hass.bus.async_fire(EVENT_UPDATED_ALERT, curr_map[common_id])
            if curr_type == "Cancel" and prev_type != "Cancel":
                self.hass.bus.async_fire(EVENT_CANCELED_ALERT, curr_map[common_id])
