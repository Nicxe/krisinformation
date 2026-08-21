"""Shared helpers for the Krisinformation integration."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from .const import COUNTY_MAPPING, DOMAIN, MUNICIPALITY_MAPPING

if TYPE_CHECKING:
    from .models import ContentArea


def legacy_location_slug(location: str) -> str:
    """Return the location slug used by releases before stable entity IDs."""
    return (
        location.lower()
        .replace(" ", "_")
        .replace("å", "a")
        .replace("ä", "a")
        .replace("ö", "o")
        .replace("é", "e")
    )


def vma_count_unique_id(entry_id: str) -> str:
    """Return the stable unique ID for the VMA count sensor."""
    return f"{DOMAIN}_{entry_id}_vma_count"


def vma_active_unique_id(entry_id: str) -> str:
    """Return the stable unique ID for the active VMA binary sensor."""
    return f"{DOMAIN}_{entry_id}_vma_active"


def vma_device_identifier(entry_id: str) -> tuple[str, str]:
    """Return the stable device identifier for the VMA source."""
    return (DOMAIN, f"{entry_id}_vma")


def county_code_for_location(location: str) -> str | None:
    """Return the county code used by Krisinformation for a configured location."""
    if location in COUNTY_MAPPING:
        return COUNTY_MAPPING[location]
    if municipality_code := MUNICIPALITY_MAPPING.get(location):
        return municipality_code[:2]
    return None


def county_name_for_location(location: str) -> str | None:
    """Return the county name represented by a county or municipality selection."""
    county_code = county_code_for_location(location)
    if county_code is None:
        return None
    return next(
        (name for name, code in COUNTY_MAPPING.items() if code == county_code), None
    )


def content_matches_geography(
    areas: Iterable[ContentArea],
    location: str,
    *,
    include_national: bool,
    include_unlocated: bool,
) -> bool:
    """Return whether Krisinformation content matches the configured geography."""
    areas = tuple(areas)
    if not areas:
        return include_unlocated

    county_name = county_name_for_location(location)
    for area in areas:
        area_type = area.type.casefold()
        description = area.description.casefold()
        if area_type == "country" or description == "sverige":
            if include_national:
                return True
            continue
        if county_name is None:
            return True
        if area_type == "county" and description == county_name.casefold():
            return True
    return False
