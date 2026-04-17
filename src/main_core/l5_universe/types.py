"""Configuration types for L5 universe selection."""

from __future__ import annotations

from dataclasses import dataclass

from main_core.common.errors import MainCoreError

MAX_OFFICIAL_ALPHA_POOL_CAPACITY = 100


@dataclass(frozen=True)
class PoolSelectionConfig:
    """Runtime configuration for observation and official alpha pool selection."""

    capacity: int = MAX_OFFICIAL_ALPHA_POOL_CAPACITY
    observation_limit: int | None = None
    min_candidate_score: float | None = None

    def __post_init__(self) -> None:
        """Validate the formal capacity hard bound before a pool is built."""

        if not isinstance(self.capacity, int) or isinstance(self.capacity, bool):
            raise MainCoreError("official_alpha_pool_capacity must be an integer")
        if not 1 <= self.capacity <= MAX_OFFICIAL_ALPHA_POOL_CAPACITY:
            raise MainCoreError(
                "official_alpha_pool_capacity must be between 1 and 100",
            )
        if (
            self.observation_limit is not None
            and (
                not isinstance(self.observation_limit, int)
                or isinstance(self.observation_limit, bool)
                or self.observation_limit < 0
            )
        ):
            raise MainCoreError("observation_limit must be a non-negative integer")


__all__ = ["MAX_OFFICIAL_ALPHA_POOL_CAPACITY", "PoolSelectionConfig"]
