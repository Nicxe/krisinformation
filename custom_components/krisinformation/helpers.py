"""Shared helpers for the Krisinformation integration."""

from __future__ import annotations

from .const import DOMAIN


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
