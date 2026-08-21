"""Async client for the public Krisinformation API v3."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession
import async_timeout
from homeassistant.const import __version__ as HA_VERSION

from .const import (
    DEFAULT_TIMEOUT_SECONDS,
    INTEGRATION_VERSION,
    KRISINFORMATION_NEWS_URL,
    KRISINFORMATION_NOTICES_URL,
    NEWS_DEFAULT_DAYS,
    USER_AGENT_PRODUCT,
)
from .models import NewsItem, NoticeItem


class KrisinformationApiError(Exception):
    """Base error raised for Krisinformation API failures."""


class KrisinformationApiConnectionError(KrisinformationApiError):
    """Raised when the Krisinformation API cannot be reached."""


class KrisinformationApiResponseError(KrisinformationApiError):
    """Raised when the Krisinformation API returns an invalid response."""


def integration_user_agent() -> str:
    """Return the integration user agent sent to upstream APIs."""
    return (
        f"{USER_AGENT_PRODUCT}/{INTEGRATION_VERSION or '0.0.0'} "
        f"HomeAssistant/{HA_VERSION or 'unknown'}"
    )


class KrisinformationApiClient:
    """Fetch and normalize Krisinformation news and notices."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._headers = {
            "Accept": "application/json",
            "User-Agent": integration_user_agent(),
        }

    @staticmethod
    def _language_code(language: str) -> str:
        return language.split("-", maxsplit=1)[0].lower()

    @staticmethod
    def _geography_params(
        county_codes: Iterable[str] | None, all_counties: bool
    ) -> dict[str, str]:
        params = {"allCounties": str(all_counties).lower()}
        if county_codes:
            params["counties"] = ",".join(county_codes)
        return params

    async def _async_get(
        self, url: str, params: dict[str, str]
    ) -> list[dict[str, Any]]:
        try:
            async with async_timeout.timeout(DEFAULT_TIMEOUT_SECONDS):
                async with self._session.get(
                    url, params=params, headers=self._headers
                ) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
        except asyncio.TimeoutError as err:
            raise KrisinformationApiConnectionError(
                f"Request timed out after {DEFAULT_TIMEOUT_SECONDS} seconds"
            ) from err
        except ClientResponseError as err:
            raise KrisinformationApiResponseError(
                f"API returned HTTP {err.status}: {err.message}"
            ) from err
        except ClientError as err:
            raise KrisinformationApiConnectionError(str(err)) from err
        except (TypeError, ValueError) as err:
            raise KrisinformationApiResponseError("API returned invalid JSON") from err

        if not isinstance(payload, list) or not all(
            isinstance(item, dict) for item in payload
        ):
            raise KrisinformationApiResponseError("API response is not a list of items")
        return payload

    async def async_get_news(
        self,
        *,
        language: str,
        county_codes: Iterable[str] | None = None,
        all_counties: bool = True,
        days: int = NEWS_DEFAULT_DAYS,
        number_of_articles: int | None = None,
        include_test: bool = False,
    ) -> tuple[NewsItem, ...]:
        """Return normalized news ordered from newest to oldest."""
        params = {
            "format": "json",
            "language": self._language_code(language),
            "includeTest": str(include_test).lower(),
            **self._geography_params(county_codes, all_counties),
        }
        if number_of_articles is None:
            params["days"] = str(days)
        else:
            params["numberOfNewsArticles"] = str(number_of_articles)

        payload = await self._async_get(KRISINFORMATION_NEWS_URL, params)
        items = (NewsItem.from_api(item) for item in payload)
        return tuple(
            sorted(
                (item for item in items if item.identifier),
                key=lambda item: item.sort_datetime,
                reverse=True,
            )
        )

    async def async_get_notices(
        self,
        *,
        language: str,
        county_codes: Iterable[str] | None = None,
        all_counties: bool = True,
    ) -> tuple[NoticeItem, ...]:
        """Return normalized notices ordered from newest to oldest."""
        params = {
            "format": "json",
            "language": self._language_code(language),
            **self._geography_params(county_codes, all_counties),
        }
        payload = await self._async_get(KRISINFORMATION_NOTICES_URL, params)
        items = (NoticeItem.from_api(item) for item in payload)
        return tuple(
            sorted(
                (item for item in items if item.identifier),
                key=lambda item: item.sort_datetime,
                reverse=True,
            )
        )
