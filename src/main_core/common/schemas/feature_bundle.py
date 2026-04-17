"""L3 runtime feature signal bundle schema."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import Field

from main_core.common.schemas.base import FormalObjectBase
from main_core.common.types import CycleId, EntityId


def _utc_now() -> datetime:
    return datetime.now(UTC)


class FeatureSignalBundle(FormalObjectBase):
    """Runtime L3 feature and signal bundle described in §9.3."""

    cycle_id: CycleId
    entity_id: EntityId
    feature_values: dict[str, float]
    signal_values: dict[str, Any]
    graph_features: dict[str, Any]
    feature_weight_multiplier: dict[str, float]
    generated_at: datetime = Field(default_factory=_utc_now)


__all__ = ["FeatureSignalBundle"]
