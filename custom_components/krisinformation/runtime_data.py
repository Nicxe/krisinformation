"""Runtime data for the Krisinformation integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import KrisinformationDataUpdateCoordinator
    from .api import KrisinformationApiClient
    from .coordinator import (
        KrisinformationNewsCoordinator,
        KrisinformationNoticesCoordinator,
    )


@dataclass
class KrisinformationRuntimeData:
    """Runtime objects belonging to a config entry."""

    vma_coordinator: KrisinformationDataUpdateCoordinator
    api_client: KrisinformationApiClient
    news_coordinator: KrisinformationNewsCoordinator
    notices_coordinator: KrisinformationNoticesCoordinator
